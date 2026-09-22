from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from models import db, User, InterviewSession, Question, Response, CommunicationAnalysis
from services.ai_agent_service import ai_agent_service
from services.communication_service import communication_service
from services import moderation_service, review_service
from datetime import datetime, timezone

interview_bp = Blueprint("interview", __name__, url_prefix="/interview")


def get_current_user():
    if "user_id" not in session:
        return None
    return db.session.get(User, session["user_id"])


@interview_bp.route("/setup", methods=["GET", "POST"])
def setup():
    user = get_current_user()
    if not user:
        flash("Please log in to start a mock interview.", "warning")
        return redirect(url_for("auth.login"))

    profile = user.profile

    if request.method == "POST":
        role = request.form.get("role", profile.target_role if profile else "Software Developer").strip()
        difficulty = request.form.get("difficulty", "Intermediate").strip()
        try:
            total_questions = int(request.form.get("total_questions", 3))
        except ValueError:
            total_questions = 3
        interview_mode = request.form.get("interview_mode", "Technical + Communication").strip()

        # Create new Interview Session
        new_session = InterviewSession(
            user_id=user.id,
            role=role,
            difficulty=difficulty,
            total_questions=total_questions,
            interview_mode=interview_mode,
            status="in_progress",
            start_time=datetime.now(timezone.utc),
        )
        db.session.add(new_session)
        db.session.commit()

        # AI Agent generates initial question (Introduction & Icebreaker)
        skills = profile.get_skills_list() if profile else []
        first_q_data = ai_agent_service.generate_first_question(
            role=role,
            difficulty=difficulty,
            skills=skills,
            candidate_name=user.name,
        )

        first_question = Question(
            interview_id=new_session.id,
            question_text=first_q_data["question_text"],
            question_type=first_q_data.get("question_type", "intro"),
            expected_concepts=first_q_data.get("expected_concepts", ""),
            difficulty_level=first_q_data.get("difficulty_level", difficulty),
            order_index=1,
        )
        db.session.add(first_question)
        db.session.commit()

        return redirect(url_for("interview.interview_room", session_id=new_session.id))

    return render_template("interview_setup.html", profile=profile)


@interview_bp.route("/<int:session_id>/room")
def interview_room(session_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        flash("Interview session not found.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if interview_session.user_id != user.id:
        flash("Unauthorized access to this interview session.", "danger")
        return redirect(url_for("dashboard.dashboard"))

    if interview_session.status == "completed":
        return redirect(url_for("interview.report", session_id=session_id))

    # Find the current pending question (the latest question without a response)
    current_question = (
        Question.query.filter_by(interview_id=session_id)
        .order_by(Question.order_index.desc())
        .first()
    )

    if not current_question or current_question.response is not None:
        # If all current questions are answered, check if session is done
        completed_count = len(interview_session.questions)
        if completed_count >= interview_session.total_questions:
            return redirect(url_for("interview.finish_interview", session_id=session_id))

    return render_template(
        "interview_room.html",
        interview=interview_session,
        question=current_question,
        current_index=current_question.order_index if current_question else 1,
        total_questions=interview_session.total_questions,
    )


@interview_bp.route("/<int:session_id>/submit-answer", methods=["POST"])
def submit_answer(session_id):
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        return jsonify({"error": "Interview session not found"}), 404

    if interview_session.user_id != user.id:
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or request.form
    transcript = data.get("transcript", "").strip()
    try:
        duration_seconds = float(data.get("duration", 10.0))
    except (ValueError, TypeError):
        duration_seconds = 10.0

    current_question_id = data.get("question_id")
    if current_question_id:
        current_question = db.session.get(Question, current_question_id)
    else:
        current_question = (
            Question.query.filter_by(interview_id=session_id)
            .order_by(Question.order_index.desc())
            .first()
        )

    if not current_question:
        return jsonify({"error": "Question not found"}), 404

    # Prevent duplicate submission
    if current_question.response:
        return jsonify({"success": True, "message": "Already answered", "next_url": url_for("interview.interview_room", session_id=session_id)})

    # ── Responsible AI: 3-Strike Content Moderation Check ────────────────────
    # Check if user is already banned or locked before accepting any answer
    if user.is_banned:
        return jsonify({
            "status": "banned",
            "message": "🚫 Your account has been permanently terminated due to policy violations. You cannot submit answers.",
        }), 403

    if user.is_account_locked():
        unlock_str = user.locked_until.strftime("%d %b %Y %H:%M UTC")
        return jsonify({
            "status": "locked",
            "message": f"🔒 Your account is temporarily suspended until {unlock_str}. Please try again after the suspension period.",
        }), 403

    # Scan the submitted transcript for policy violations
    moderation_result = moderation_service.check_and_apply(transcript, user)
    if moderation_result:
        # A strike was applied – return the moderation response without evaluating the answer
        return jsonify(moderation_result), 200

    # 1. Communication Analysis (Speed, Fillers, Pauses, Fluency, Structure)
    comm_analysis = communication_service.analyze_communication(
        transcript=transcript, duration_seconds=duration_seconds
    )

    # 2. Generative AI Technical / Introduction Evaluation
    eval_result = ai_agent_service.evaluate_response(
        question_text=current_question.question_text,
        expected_concepts=current_question.expected_concepts,
        student_transcript=transcript,
        question_type=current_question.question_type,
        difficulty=interview_session.difficulty,
    )

    # 3. Save Response in Database
    new_response = Response(
        question_id=current_question.id,
        transcript=transcript if transcript else "(No spoken response recorded)",
        correctness_score=eval_result["correctness_score"],
        qualitative_feedback=eval_result["qualitative_feedback"],
        strengths=eval_result["strengths"],
        improvements=eval_result["improvements"],
        model_answer=eval_result.get("model_answer", ""),
        audio_duration_seconds=duration_seconds,
    )
    db.session.add(new_response)
    db.session.flush()

    # 4. Save Communication Analysis
    comm_record = CommunicationAnalysis(
        response_id=new_response.id,
        speaking_speed_wpm=comm_analysis["speaking_speed_wpm"],
        filler_count=comm_analysis["filler_count"],
        filler_breakdown=comm_analysis["filler_breakdown"],
        pause_count=comm_analysis["pause_count"],
        fluency_rating=comm_analysis["fluency_rating"],
        structure_score=comm_analysis["structure_score"],
        communication_score=comm_analysis["communication_score"],
    )
    db.session.add(comm_record)
    db.session.commit()

    # 5. AI Agent Adaptive Decision: Decide next step
    agent_decision = ai_agent_service.decide_next_step(
        current_question_index=current_question.order_index,
        total_questions=interview_session.total_questions,
        role=interview_session.role,
        current_question=current_question.question_text,
        transcript=transcript,
        correctness_score=eval_result["correctness_score"],
        comm_metrics=comm_analysis,
        current_question_type=current_question.question_type,
        difficulty=interview_session.difficulty,
    )

    if agent_decision["action"] == "continue" and agent_decision["next_question"]:
        next_q_data = agent_decision["next_question"]
        next_question = Question(
            interview_id=interview_session.id,
            question_text=next_q_data["question_text"],
            question_type=next_q_data.get("question_type", agent_decision["decision_type"]),
            expected_concepts=next_q_data.get("expected_concepts", ""),
            difficulty_level=next_q_data.get("difficulty_level", interview_session.difficulty),
            order_index=current_question.order_index + 1,
        )
        db.session.add(next_question)
        db.session.commit()

        return jsonify({
            "success": True,
            "decision": agent_decision["decision_type"],
            "reason": agent_decision["reason"],
            "status": "continue",
            "next_url": url_for("interview.interview_room", session_id=session_id),
            "feedback_summary": {
                "correctness": eval_result["correctness_score"],
                "comm_score": comm_analysis["communication_score"],
                "wpm": comm_analysis["speaking_speed_wpm"],
                "fillers": comm_analysis["filler_count"],
                "agent_note": agent_decision["reason"],
            },
        })
    else:
        # Reached question limit -> finalize interview
        _finalize_session(interview_session)
        return jsonify({
            "success": True,
            "status": "completed",
            "redirect_url": url_for("interview.report", session_id=session_id),
        })


@interview_bp.route("/<int:session_id>/finish")
def finish_interview(session_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        return redirect(url_for("dashboard.dashboard"))

    if interview_session.user_id != user.id:
        return redirect(url_for("dashboard.dashboard"))

    _finalize_session(interview_session)
    return redirect(url_for("interview.report", session_id=session_id))


def _finalize_session(interview_session: InterviewSession):
    """Calculates overall session scores, averages, and generates executive feedback."""
    questions = interview_session.questions
    answered = [q for q in questions if q.response is not None]

    if answered:
        total_correctness = sum(q.response.correctness_score for q in answered)
        avg_correctness_pct = round((total_correctness / (len(answered) * 10.0)) * 100, 1)

        total_comm = sum(q.response.communication.communication_score for q in answered if q.response.communication)
        avg_comm_pct = round((total_comm / (len(answered) * 10.0)) * 100, 1)

        # Overall weighted score (50% technical correctness, 50% communication)
        overall = round((avg_correctness_pct * 0.5) + (avg_comm_pct * 0.5), 1)

        avg_wpm = round(
            sum(q.response.communication.speaking_speed_wpm for q in answered if q.response.communication)
            / len(answered),
            1,
        )
        total_fillers = sum(
            q.response.communication.filler_count for q in answered if q.response.communication
        )
        total_pauses = sum(
            q.response.communication.pause_count for q in answered if q.response.communication
        )

        interview_session.overall_score = overall
        interview_session.technical_score = avg_correctness_pct
        interview_session.communication_score = avg_comm_pct
        interview_session.avg_wpm = avg_wpm
        interview_session.total_fillers = total_fillers
        interview_session.total_pauses = total_pauses

        # Summary bullet points
        strengths = []
        improvements = []
        if avg_correctness_pct >= 75:
            strengths.append("High technical conceptual accuracy and depth.")
        else:
            improvements.append("Deepen foundational technical concepts and state definitions accurately.")

        if avg_comm_pct >= 75:
            strengths.append("Crisp articulation with strong sentence cadence.")
        else:
            improvements.append("Reduce hesitation and structure answers with clear premises.")

        if total_fillers <= 3:
            strengths.append("Excellent verbal discipline with minimal filler words.")
        else:
            improvements.append(f"Cut down on filler words ({total_fillers} detected); leverage silent pauses.")

        if 115 <= avg_wpm <= 155:
            strengths.append(f"Ideal speaking pace ({avg_wpm} WPM) for a professional interview.")
        else:
            improvements.append(f"Calibrate pacing towards the 120-145 WPM benchmark (currently {avg_wpm} WPM).")

        interview_session.summary_strengths = "\n".join(strengths)
        interview_session.summary_improvements = "\n".join(improvements)

    interview_session.status = "completed"
    interview_session.end_time = datetime.now(timezone.utc)
    db.session.commit()


@interview_bp.route("/<int:session_id>/report")
def report(session_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("auth.login"))

    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        flash("Interview session not found.", "warning")
        return redirect(url_for("dashboard.dashboard"))

    if interview_session.user_id != user.id:
        return redirect(url_for("dashboard.dashboard"))

    questions = interview_session.questions
    return render_template(
        "report.html",
        interview=interview_session,
        questions=questions,
        user=user,
    )


# ── Responsible AI: Human Oversight – Mentor Review ──────────────────────────

@interview_bp.route("/<int:session_id>/request-review", methods=["POST"])
def request_review(session_id):
    """
    Student-initiated mentor review request.
    Records the request in the database and flags the session for human review.
    This implements the minimal "Request Review" button feature per Responsible AI plan.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        return jsonify({"error": "Session not found"}), 404

    if interview_session.user_id != user.id:
        return jsonify({"error": "Forbidden"}), 403

    if interview_session.status != "completed":
        return jsonify({"error": "Can only request review for completed sessions"}), 400

    data = request.get_json() or {}
    note = data.get("note", "").strip()

    review = review_service.create_review_request(
        session=interview_session,
        user_id=user.id,
        note=note,
    )

    return jsonify({
        "success": True,
        "message": "✅ Your review request has been submitted. A mentor will evaluate your session and provide feedback.",
        "review_id": review.id,
        "status": review.status,
    })


# ── Responsible AI: Privacy & Security – Right to be Forgotten ───────────────

@interview_bp.route("/<int:session_id>/delete", methods=["POST"])
def delete_session(session_id):
    """
    Permanently delete a student's interview session data (Right to be Forgotten).
    Cascades to Questions, Responses, CommunicationAnalysis, and ScoreReviews.
    """
    user = get_current_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    interview_session = db.session.get(InterviewSession, session_id)
    if not interview_session:
        return jsonify({"error": "Session not found"}), 404

    if interview_session.user_id != user.id:
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(interview_session)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": "🗑️ Your interview session data has been permanently deleted.",
        "redirect_url": url_for("dashboard.dashboard"),
    })
