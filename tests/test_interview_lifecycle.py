import pytest
from app import create_app
from models import db, User, Profile, InterviewSession, Question


@pytest.fixture
def client_with_user():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        user = User(name="Test Candidate", email="candidate@test.com", is_verified=True)
        user.set_password("pass123")
        db.session.add(user)
        db.session.commit()

        profile = Profile(
            user_id=user.id,
            education="B.Tech",
            branch="CSE",
            college="Chitkara",
            cgpa=8.8,
            graduation_year=2026,
            technical_skills="Java, DSA, SQL",
            experience="Fresher",
            target_role="Software Developer",
        )
        db.session.add(profile)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess["user_id"] = user.id
            sess["user_name"] = user.name

        yield client, app, user


def test_full_interview_lifecycle(client_with_user):
    client, app, user = client_with_user

    # 1. Setup Interview (3 questions)
    setup_resp = client.post(
        "/interview/setup",
        data={
            "role": "Software Developer",
            "difficulty": "Intermediate",
            "total_questions": 3,
            "interview_mode": "Technical + Communication",
        },
        follow_redirects=True,
    )
    assert setup_resp.status_code == 200
    assert b"Question 1 of 3" in setup_resp.data

    with app.app_context():
        session_obj = InterviewSession.query.filter_by(user_id=user.id).first()
        assert session_obj is not None
        assert session_obj.status == "in_progress"
        session_id = session_obj.id

        q1 = Question.query.filter_by(interview_id=session_id, order_index=1).first()
        assert q1 is not None
        q1_id = q1.id

    # 2. Submit Question 1 Answer (Candidate Introduction) -> Agent transitions to technical
    ans1_resp = client.post(
        f"/interview/{session_id}/submit-answer",
        json={
            "transcript": "Hello, I am a final-year Computer Science student at Chitkara University. Over the past year I have worked on web applications using Java and Python, and I am passionate about software engineering and solving real-world challenges.",
            "duration": 20.0,
            "question_id": q1_id,
        },
    )
    assert ans1_resp.status_code == 200
    ans1_data = ans1_resp.get_json()
    assert ans1_data["status"] == "continue"
    assert ans1_data["decision"] == "transition_technical"

    # 3. Verify Question 2 was generated as core technical
    with app.app_context():
        q2 = Question.query.filter_by(interview_id=session_id, order_index=2).first()
        assert q2 is not None
        assert q2.question_type == "transition_technical"
        q2_id = q2.id

    # 4. Submit Question 2 Answer (With high fillers 'um', 'basically') -> Agent gives structured follow-up
    ans2_resp = client.post(
        f"/interview/{session_id}/submit-answer",
        json={
            "transcript": "Well, um, basically the vtable is, like, a table of function pointers, um, basically used by JVM.",
            "duration": 12.0,
            "question_id": q2_id,
        },
    )
    assert ans2_resp.status_code == 200
    ans2_data = ans2_resp.get_json()
    assert ans2_data["status"] == "continue"

    # 5. Submit Question 3 (Final Question) -> Agent completes interview
    with app.app_context():
        q3 = Question.query.filter_by(interview_id=session_id, order_index=3).first()
        assert q3 is not None
        q3_id = q3.id

    ans3_resp = client.post(
        f"/interview/{session_id}/submit-answer",
        json={
            "transcript": "Database indexes use B-trees to provide logarithmic search complexity O(log n), speeding up query lookups over full table scans.",
            "duration": 15.0,
            "question_id": q3_id,
        },
    )
    assert ans3_resp.status_code == 200
    ans3_data = ans3_resp.get_json()
    assert ans3_data["status"] == "completed"
    assert "report" in ans3_data["redirect_url"]

    # 6. Verify Session is finalized with scores
    with app.app_context():
        session_final = db.session.get(InterviewSession, session_id)
        assert session_final.status == "completed"
        assert session_final.overall_score > 0
        assert session_final.technical_score > 0
        assert session_final.communication_score > 0
        assert session_final.avg_wpm > 0

    # 7. Access Final Report page
    report_resp = client.get(f"/interview/{session_id}/report")
    assert report_resp.status_code == 200
    assert b"Interview Performance Report" in report_resp.data
    assert b"Response Correctness" in report_resp.data
    assert b"Communication Delivery" in report_resp.data
