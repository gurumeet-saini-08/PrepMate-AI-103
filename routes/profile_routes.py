from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models import db, User, Profile

profile_bp = Blueprint("profile", __name__)


def login_required():
    return "user_id" in session


@profile_bp.route("/profile", methods=["GET", "POST"])
def profile_setup():
    if not login_required():
        flash("Please log in to manage your profile.", "warning")
        return redirect(url_for("auth.login"))

    user = db.session.get(User, session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    profile = user.profile
    if not profile:
        profile = Profile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        profile.education = request.form.get("education", "").strip()
        profile.branch = request.form.get("branch", "").strip()
        profile.college = request.form.get("college", "").strip()
        
        cgpa_str = request.form.get("cgpa", "").strip()
        if cgpa_str:
            try:
                profile.cgpa = float(cgpa_str)
            except ValueError:
                profile.cgpa = None
        else:
            profile.cgpa = None

        grad_str = request.form.get("graduation_year", "").strip()
        if grad_str:
            try:
                profile.graduation_year = int(grad_str)
            except ValueError:
                profile.graduation_year = None
        else:
            profile.graduation_year = None

        profile.technical_skills = request.form.get("technical_skills", "").strip()
        profile.experience = request.form.get("experience", "").strip()
        profile.target_role = request.form.get("target_role", "").strip()

        db.session.commit()
        flash("Profile updated successfully! AI Agent will customize your interviews based on these skills.", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("profile.html", user=user, profile=profile)
