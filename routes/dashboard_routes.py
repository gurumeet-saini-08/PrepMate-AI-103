from flask import Blueprint, render_template, redirect, url_for, flash, session
from models import db, User, Profile, InterviewSession
from services.coach_service import coach_service
from config import Config

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        flash("Please log in to access your student dashboard.", "info")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    profile = user.profile
    interviews = (
        InterviewSession.query.filter_by(user_id=user.id)
        .order_by(InterviewSession.start_time.desc())
        .all()
    )

    completed_interviews = [i for i in interviews if i.status == "completed"]
    
    # Calculate aggregate performance statistics
    avg_overall = 0.0
    avg_tech = 0.0
    avg_comm = 0.0
    avg_wpm = 0.0
    if completed_interviews:
        avg_overall = round(sum(i.overall_score for i in completed_interviews) / len(completed_interviews), 1)
        avg_tech = round(sum(i.technical_score for i in completed_interviews) / len(completed_interviews), 1)
        avg_comm = round(sum(i.communication_score for i in completed_interviews) / len(completed_interviews), 1)
        avg_wpm = round(sum(i.avg_wpm for i in completed_interviews if i.avg_wpm > 0) / max(1, sum(1 for i in completed_interviews if i.avg_wpm > 0)), 1)

    # Get or generate personalized Daily Coach recommendation
    daily_tip = coach_service.get_or_generate_daily_tip(user.id)
    system_mode = Config.get_system_mode()

    return render_template(
        "dashboard.html",
        user=user,
        profile=profile,
        interviews=interviews[:5],  # Recent 5 sessions
        total_interviews=len(completed_interviews),
        avg_overall=avg_overall,
        avg_tech=avg_tech,
        avg_comm=avg_comm,
        avg_wpm=avg_wpm,
        daily_tip=daily_tip,
        system_mode=system_mode,
    )


@dashboard_bp.route("/history")
def history():
    if "user_id" not in session:
        return redirect(url_for("auth.login"))

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    interviews = (
        InterviewSession.query.filter_by(user_id=user.id)
        .order_by(InterviewSession.start_time.desc())
        .all()
    )
    return render_template("history.html", user=user, interviews=interviews)
