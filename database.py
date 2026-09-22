from models import db, User, Profile, DailyTip
from datetime import datetime, timezone


def init_db(app):
    """Initializes the database and pre-seeds a demo student account if none exists."""
    with app.app_context():
        db.create_all()

        # Check if demo student exists
        demo_user = User.query.filter_by(email="student@chitkara.edu.in").first()
        if not demo_user:
            demo_user = User(
                name="Aarav Sharma",
                email="student@chitkara.edu.in",
                is_verified=True,
            )
            demo_user.set_password("password123")
            db.session.add(demo_user)
            db.session.commit()

            # Create default profile
            profile = Profile(
                user_id=demo_user.id,
                education="B.Tech",
                branch="Computer Science & Engineering",
                college="Chitkara University",
                cgpa=8.65,
                graduation_year=2026,
                technical_skills="Java, Python, Data Structures & Algorithms, SQL, Web Development, Cloud Basics",
                experience="Fresher",
                target_role="Software Developer",
            )
            db.session.add(profile)

            # Create default welcoming daily tip
            welcome_tip = DailyTip(
                user_id=demo_user.id,
                category="Structure",
                tip_title="The STAR / PREP Method for Technical Clarity",
                tip_content="When explaining a concept or past challenge, structure your response as: Point → Reason → Example → Point. This immediately boosts your communication rating.",
                practice_exercise="Explain 'Why do we use indexes in SQL databases?' in 60 seconds using Point-Reason-Example.",
                date_generated=datetime.now(timezone.utc).date(),
            )
            db.session.add(welcome_tip)
            db.session.commit()
            print("[Database] Initialized tables and seeded demo student: student@chitkara.edu.in / password123")
        else:
            print("[Database] Existing database detected, tables verified.")
