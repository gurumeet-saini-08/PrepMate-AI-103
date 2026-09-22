import pytest
from app import create_app
from models import db, User, Profile


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def test_landing_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"PrepMate" in response.data
    assert b"AI-103" in response.data


def test_responsible_ai_page(client):
    response = client.get("/responsible-ai")
    assert response.status_code == 200
    assert b"Responsible AI" in response.data


def test_api_system_status(client):
    response = client.get("/api/system-status")
    assert response.status_code == 200
    json_data = response.get_json()
    assert "mode" in json_data
    assert "fallback_enabled" in json_data


def test_registration_and_login_flow(client):
    # 1. Register new user
    res = client.post(
        "/register",
        data={"name": "Priya Patel", "email": "priya@chitkara.edu.in", "password": "securepassword"},
        follow_redirects=True,
    )
    assert res.status_code == 200
    assert b"Welcome to PrepMate" in res.data or b"Student Profile Setup" in res.data

    # 2. Access dashboard
    res2 = client.get("/dashboard")
    assert res2.status_code == 200
    assert b"Priya Patel" in res2.data


def test_api_transcribe_audio_validation(client):
    res = client.post("/api/transcribe-audio")
    assert res.status_code == 400
    assert res.get_json()["error"] == "No audio file provided"


def test_api_synthesize_speech_validation(client):
    res = client.post("/api/synthesize-speech", json={})
    assert res.status_code == 400
    assert res.get_json()["error"] == "No text provided"

    # Valid text request (when Azure key is blank, gracefully recommends browser synthesis fallback)
    res_valid = client.post("/api/synthesize-speech", json={"text": "Hello candidate"})
    assert res_valid.status_code == 200
    json_data = res_valid.get_json()
    assert "success" in json_data

