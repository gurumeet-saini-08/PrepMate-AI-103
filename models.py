from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
import json

db = SQLAlchemy()


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_verified = db.Column(db.Boolean, default=True)  # Auto-verified for seamless local demo
    created_at = db.Column(db.DateTime, default=utc_now)

    # ── Responsible AI: 3-Strike Content-Moderation fields ──────────────────────
    strike_count = db.Column(db.Integer, default=0)         # 0, 1, 2, 3
    locked_until = db.Column(db.DateTime, nullable=True)    # UTC datetime when lock expires
    is_banned = db.Column(db.Boolean, default=False)        # Permanent ban flag

    # Relationships
    profile = db.relationship("Profile", backref="user", uselist=False, cascade="all, delete-orphan")
    interviews = db.relationship("InterviewSession", backref="user", lazy=True, cascade="all, delete-orphan")
    daily_tips = db.relationship("DailyTip", backref="user", lazy=True, cascade="all, delete-orphan")
    score_reviews = db.relationship("ScoreReview", backref="user", lazy=True, cascade="all, delete-orphan")

    def set_password(self, password: str):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def is_account_locked(self) -> bool:
        """Returns True if the account is currently under a temporary lock."""
        if self.locked_until and self.locked_until > datetime.now(timezone.utc):
            return True
        return False

    def __repr__(self):
        return f"<User {self.email}>"


class BlockedIdentity(db.Model):
    """Permanent email blacklist – prevents re-registration after a 3rd strike."""
    __tablename__ = "blocked_identities"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    reason = db.Column(db.String(255), default="Policy violation – 3-strike rule exceeded")
    banned_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<BlockedIdentity {self.email}>"


class Profile(db.Model):
    __tablename__ = "profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    education = db.Column(db.String(100), default="", nullable=True)
    branch = db.Column(db.String(100), default="", nullable=True)
    college = db.Column(db.String(150), default="", nullable=True)
    cgpa = db.Column(db.Float, nullable=True)
    graduation_year = db.Column(db.Integer, nullable=True)
    technical_skills = db.Column(db.Text, default="", nullable=True)
    experience = db.Column(db.String(50), default="", nullable=True)  # Fresher, Internship, Experienced
    target_role = db.Column(db.String(100), default="", nullable=True)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    def get_skills_list(self):
        if not self.technical_skills:
            return []
        return [s.strip() for s in self.technical_skills.split(",") if s.strip()]

    def completion_percentage(self) -> int:
        fields = [self.education, self.branch, self.college, self.cgpa, self.graduation_year, self.technical_skills, self.experience, self.target_role]
        filled = sum(1 for f in fields if f is not None and str(f).strip() != "")
        return int((filled / len(fields)) * 100)


class InterviewSession(db.Model):
    __tablename__ = "interview_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), default="Intermediate")  # Beginner, Intermediate, Advanced
    total_questions = db.Column(db.Integer, default=5)
    interview_mode = db.Column(db.String(50), default="Technical + Communication")
    status = db.Column(db.String(50), default="in_progress")  # in_progress, completed, abandoned
    
    # Aggregated Scores (0-100)
    overall_score = db.Column(db.Float, default=0.0)
    technical_score = db.Column(db.Float, default=0.0)
    communication_score = db.Column(db.Float, default=0.0)
    
    # Communication averages
    avg_wpm = db.Column(db.Float, default=0.0)
    total_fillers = db.Column(db.Integer, default=0)
    total_pauses = db.Column(db.Integer, default=0)

    # Executive Summary Feedback
    summary_strengths = db.Column(db.Text, default="")
    summary_improvements = db.Column(db.Text, default="")

    # ── Responsible AI: Human Oversight – Mentor Review ─────────────────────────
    mentor_review_requested = db.Column(db.Boolean, default=False)

    start_time = db.Column(db.DateTime, default=utc_now)
    end_time = db.Column(db.DateTime, nullable=True)

    # Relationships
    questions = db.relationship("Question", backref="interview", lazy=True, cascade="all, delete-orphan", order_by="Question.order_index")
    score_reviews = db.relationship("ScoreReview", backref="session", lazy=True, cascade="all, delete-orphan")

    def duration_formatted(self) -> str:
        if not self.end_time or not self.start_time:
            return "Active"
        delta = self.end_time - self.start_time
        mins = int(delta.total_seconds() // 60)
        secs = int(delta.total_seconds() % 60)
        return f"{mins}m {secs}s"


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    interview_id = db.Column(db.Integer, db.ForeignKey("interview_sessions.id"), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(50), default="core")  # core, follow_up, simplified, advanced
    expected_concepts = db.Column(db.Text, default="")
    difficulty_level = db.Column(db.String(50), default="Intermediate")
    order_index = db.Column(db.Integer, default=1)

    # Relationships
    response = db.relationship("Response", backref="question", uselist=False, cascade="all, delete-orphan")


class Response(db.Model):
    __tablename__ = "responses"

    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False, unique=True)
    transcript = db.Column(db.Text, nullable=False)
    correctness_score = db.Column(db.Float, default=0.0)  # Scale 0.0 to 10.0
    qualitative_feedback = db.Column(db.Text, default="")
    strengths = db.Column(db.Text, default="")
    improvements = db.Column(db.Text, default="")
    model_answer = db.Column(db.Text, default="")
    audio_duration_seconds = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    communication = db.relationship("CommunicationAnalysis", backref="response", uselist=False, cascade="all, delete-orphan")


class CommunicationAnalysis(db.Model):
    __tablename__ = "communication_analyses"

    id = db.Column(db.Integer, primary_key=True)
    response_id = db.Column(db.Integer, db.ForeignKey("responses.id"), nullable=False, unique=True)
    
    speaking_speed_wpm = db.Column(db.Float, default=0.0)
    filler_count = db.Column(db.Integer, default=0)
    filler_breakdown = db.Column(db.Text, default="{}")  # JSON encoded { 'um': 2, 'like': 1 }
    pause_count = db.Column(db.Integer, default=0)
    fluency_rating = db.Column(db.String(50), default="Good")  # Needs Improvement, Moderate, Good, Excellent
    structure_score = db.Column(db.Float, default=7.0)  # 0 to 10
    communication_score = db.Column(db.Float, default=7.0)  # 0 to 10

    def get_filler_breakdown_dict(self):
        try:
            return json.loads(self.filler_breakdown or "{}")
        except Exception:
            return {}


class DailyTip(db.Model):
    __tablename__ = "daily_tips"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    category = db.Column(db.String(50), default="Communication")  # Communication, Structure, Technical
    tip_title = db.Column(db.String(150), nullable=False)
    tip_content = db.Column(db.Text, nullable=False)
    practice_exercise = db.Column(db.Text, nullable=False)
    date_generated = db.Column(db.Date, default=lambda: datetime.now(timezone.utc).date())


class ScoreReview(db.Model):
    """Responsible AI – Human Oversight: records student-initiated mentor review requests."""
    __tablename__ = "score_reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    session_id = db.Column(db.Integer, db.ForeignKey("interview_sessions.id"), nullable=False)
    note = db.Column(db.Text, nullable=True)            # Optional student note / reason for contest
    requested_at = db.Column(db.DateTime, default=utc_now)
    # Status: pending → handled/accepted/adjusted/rejected
    status = db.Column(db.String(50), default="pending")
    mentor_decision = db.Column(db.Text, nullable=True) # Mentor's response / note

    def __repr__(self):
        return f"<ScoreReview session={self.session_id} status={self.status}>"
