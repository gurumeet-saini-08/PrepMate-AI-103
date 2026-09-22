from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime, timezone
from models import db, User, Profile, BlockedIdentity

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or not password:
            flash("Please complete all required fields.", "danger")
            return render_template("auth/register.html")

        # ── Responsible AI: Check permanent email blacklist ───────────────────
        if BlockedIdentity.query.filter_by(email=email).first():
            flash(
                "Registration is not permitted for this email address due to a previous "
                "policy violation. Please contact the institution's placement coordinator.",
                "danger",
            )
            return render_template("auth/register.html")

        if User.query.filter_by(email=email).first():
            flash("An account with this email address already exists. Please login.", "warning")
            return redirect(url_for("auth.login"))

        # Create user
        new_user = User(name=name, email=email, is_verified=True)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Initialize empty student profile for the user to complete
        new_profile = Profile(
            user_id=new_user.id,
            education="",
            branch="",
            college="",
            cgpa=None,
            graduation_year=None,
            technical_skills="",
            experience="",
            target_role="",
        )
        db.session.add(new_profile)
        db.session.commit()

        session["user_id"] = new_user.id
        session["user_name"] = new_user.name
        flash(f"Welcome to PrepMate, {new_user.name}! Your account has been verified.", "success")
        return redirect(url_for("profile.profile_setup"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            flash("Invalid email or password. Please check your credentials.", "danger")
            return render_template("auth/login.html")

        # ── Responsible AI: Enforce 3-strike account restrictions ─────────────
        if user.is_banned:
            flash(
                "🚫 This account has been permanently suspended due to repeated policy "
                "violations. If you believe this is an error, contact your placement coordinator.",
                "danger",
            )
            return render_template("auth/login.html")

        if user.is_account_locked():
            unlock_str = user.locked_until.strftime("%d %b %Y %H:%M UTC")
            flash(
                f"🔒 Your account is temporarily suspended until {unlock_str} due to a "
                "policy violation. Please try again after the suspension period.",
                "warning",
            )
            return render_template("auth/login.html")

        session["user_id"] = user.id
        session["user_name"] = user.name
        flash(f"Welcome back, {user.name}!", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out safely.", "info")
    return redirect(url_for("index"))


@auth_bp.route("/verify-email")
def verify_email():
    """Demonstrates email verification status step."""
    return render_template("auth/verify.html")
