"""
services/review_service.py
══════════════════════════════════════════════════════════════════════════════
Responsible AI – Human Oversight
----------------------------------
Helper functions for the "Request Mentor Review / Contest Score" feature.
Students can flag an AI-generated score for human professor review after
their interview. The request is persisted to the database (ScoreReview)
and sets a flag on the InterviewSession.
══════════════════════════════════════════════════════════════════════════════
"""

from datetime import datetime, timezone
from models import db, InterviewSession, ScoreReview


def create_review_request(session: InterviewSession, user_id: int, note: str = "") -> ScoreReview:
    """
    Create a new ScoreReview record and flag the session as having a
    pending mentor review.

    Args:
        session:  The InterviewSession the student wants reviewed.
        user_id:  ID of the student requesting the review.
        note:     Optional free-text note explaining why the score is contested.

    Returns:
        The newly created ScoreReview ORM object.
    """
    # Create the review record
    review = ScoreReview(
        user_id=user_id,
        session_id=session.id,
        note=note.strip() if note else "",
        requested_at=datetime.now(timezone.utc),
        status="pending",
    )
    db.session.add(review)

    # Flag the session so mentors can filter by it
    session.mentor_review_requested = True

    db.session.commit()
    return review


def get_pending_reviews():
    """Return all ScoreReview records with status='pending', ordered by request time."""
    return (
        ScoreReview.query
        .filter_by(status="pending")
        .order_by(ScoreReview.requested_at.asc())
        .all()
    )
