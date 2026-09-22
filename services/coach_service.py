from models import DailyTip, InterviewSession, db
from datetime import datetime, date


class CoachService:
    """
    Daily Coach Recommendation Engine:
    Generates personalized daily actionable tips and 60-second micro-practices
    based on the student's recent interview trends and weaknesses.
    """

    def get_or_generate_daily_tip(self, user_id: int) -> DailyTip:
        today = date.today()
        # Check if tip already generated today
        existing_tip = DailyTip.query.filter_by(user_id=user_id, date_generated=today).first()
        if existing_tip:
            return existing_tip

        # Fetch latest completed interview session
        last_session = (
            InterviewSession.query.filter_by(user_id=user_id, status="completed")
            .order_by(InterviewSession.end_time.desc())
            .first()
        )

        # Decide tip focus based on previous weaknesses
        if last_session:
            total_fillers = last_session.total_fillers
            avg_wpm = last_session.avg_wpm
            tech_score = last_session.technical_score
            comm_score = last_session.communication_score

            if total_fillers >= 6:
                category = "Filler Reduction"
                title = "The Power of the Silent Pause"
                content = (
                    f"Your last interview had {total_fillers} filler words (such as 'um', 'basically', 'like'). "
                    "When gathering your thoughts, replace filler words with a deliberate 1-second silence. "
                    "Silence conveys thoughtfulness and confidence."
                )
                practice = "Pick any technical term (e.g. 'Recursion') and record yourself explaining it for 60 seconds without uttering a single 'um' or 'basically'."
            elif avg_wpm < 105:
                category = "Speech Cadence"
                title = "Energize Your Conversational Pace"
                content = (
                    f"Your average speaking speed was {avg_wpm} WPM. While thoughtful, a pace below 110 WPM can sound hesitant. "
                    "Aim for a lively, conversational cadence between 125-145 WPM."
                )
                practice = "Read a short paragraph of technical documentation out loud with an energetic, brisk conversational tempo."
            elif avg_wpm > 165:
                category = "Pacing & Articulation"
                title = "Pacing Under Pressure"
                content = (
                    f"Your speaking speed clocked at {avg_wpm} WPM. When speaking fast, key technical keywords get compressed. "
                    "Practice breathing between sentences to ensure the interviewer absorbs every key concept."
                )
                practice = "Explain 'How a Hash Map works' at a deliberate, steady pace of 130 WPM."
            elif tech_score < 70:
                category = "Technical Depth"
                title = "Anchor Concepts With Concrete Examples"
                content = (
                    "In technical interviews, pure definitions receive partial credit. "
                    "Whenever you define a principle, immediately follow it with: 'For example, in a banking application...'"
                )
                practice = "Explain 'ACID properties in DBMS' and dedicate 30 seconds specifically to an example transaction."
            else:
                category = "Executive Presence"
                title = "The PREP Communication Framework"
                content = (
                    "Your technical foundation is strong! Level up to Senior Candidate level by structuring every response as: "
                    "Point (direct answer) → Reason (architectural why) → Example (concrete code/use case) → Point (reiterate)."
                )
                practice = "Answer 'Why is immutability preferred in concurrent systems?' strictly adhering to the PREP method."
        else:
            # Welcome tip for brand new students
            category = "Foundations"
            title = "Welcome to PrepMate Daily Coach!"
            content = (
                "Preparation isn't just about what you know—it's how clearly you communicate it under pressure. "
                "PrepMate tracks both your Technical Accuracy and Speaking Delivery."
            )
            practice = "Complete your first 3-question mock interview to unlock tailored coaching metrics!"

        new_tip = DailyTip(
            user_id=user_id,
            category=category,
            tip_title=title,
            tip_content=content,
            practice_exercise=practice,
            date_generated=today,
        )
        db.session.add(new_tip)
        db.session.commit()
        return new_tip


# Singleton instance
coach_service = CoachService()
