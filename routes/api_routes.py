import os
import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, session, send_from_directory
from config import Config
from services.speech_service import speech_service

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/system-status", methods=["GET"])
def system_status():
    """Returns real-time status of Azure resources and system fallback mode."""
    return jsonify(Config.get_system_mode())


@api_bp.route("/audio/<filename>")
def serve_audio(filename):
    """Serves synthesized audio files from the temporary audio upload directory."""
    return send_from_directory(Config.UPLOAD_FOLDER, filename)


@api_bp.route("/transcribe-audio", methods=["POST"])
def transcribe_audio():
    """
    Accepts recorded audio blob (WAV/WEBM) from browser MediaRecorder,
    saves temporarily, and invokes Azure AI Speech service to transcribe.
    """
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "No audio file provided"}), 400

    audio_file = request.files["audio"]
    if audio_file.filename == "":
        return jsonify({"success": False, "error": "Empty audio file"}), 400

    # Ensure upload directory exists
    upload_dir = Config.UPLOAD_FOLDER
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Save temporary audio file
    filename = f"speech_{uuid.uuid4().hex[:8]}.wav"
    temp_path = upload_dir / filename
    audio_file.save(str(temp_path))

    try:
        # Transcribe using SpeechService
        result = speech_service.transcribe_audio_file(str(temp_path))
        return jsonify(result)
    finally:
        # Cleanup temporary audio file
        if temp_path.exists():
            try:
                os.remove(str(temp_path))
            except Exception:
                pass


@api_bp.route("/synthesize-speech", methods=["POST"])
def synthesize_speech():
    """
    Synthesizes interview question text to audio using Azure TTS JennyNeural.
    """
    data = request.get_json() or {}
    text = data.get("text", "").strip()
    if not text:
        return jsonify({"success": False, "error": "No text provided"}), 400

    upload_dir = Config.UPLOAD_FOLDER
    upload_dir.mkdir(parents=True, exist_ok=True)
    out_filename = f"tts_{uuid.uuid4().hex[:8]}.wav"
    out_path = upload_dir / out_filename

    success = speech_service.synthesize_speech(text, str(out_path))
    if success and out_path.exists():
        return jsonify({"success": True, "audio_url": f"/api/audio/{out_filename}"})
    else:
        return jsonify({"success": False, "message": "Browser speech synthesis recommended."})

