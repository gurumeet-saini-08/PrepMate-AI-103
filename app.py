import os
from flask import Flask, render_template, session, redirect, url_for
from config import Config
from models import db
from database import init_db
from routes.auth_routes import auth_bp
from routes.profile_routes import profile_bp
from routes.dashboard_routes import dashboard_bp
from routes.interview_routes import interview_bp
from routes.api_routes import api_bp


def create_app():
    """Application factory for PrepMate."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize database
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(api_bp)

    # Root route - Landing page
    @app.route("/")
    def index():
        if "user_id" in session:
            return redirect(url_for("dashboard.dashboard"))
        system_mode = Config.get_system_mode()
        return render_template("index.html", system_mode=system_mode)

    # Responsible AI transparency page for AI-103 rubric
    @app.route("/responsible-ai")
    def responsible_ai():
        return render_template("responsible_ai.html")

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template("base.html", error_title="Page Not Found", error_msg="The requested page could not be located."), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("base.html", error_title="System Error", error_msg="An unexpected error occurred. Please try again."), 500

    # Ensure upload directory exists
    Config.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

    # Initialize tables and seed demo student
    init_db(app)

    return app


app = create_app()

if __name__ == "__main__":
    print(f"📡 Operating Mode: {Config.get_system_mode()['mode']}")
    app.run(host="127.0.0.1", port=5000, debug=True)