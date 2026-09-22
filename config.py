import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory of the application
BASE_DIR = Path(__file__).resolve().parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")


class Config:
    """Base application configuration with Azure service status detection."""

    SECRET_KEY = os.getenv("SECRET_KEY", "prepmate-dev-key-chitkara-ai103-2026")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'prepmate.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Audio & Upload Directories
    UPLOAD_FOLDER = BASE_DIR / "temp_audio"
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max audio upload

    # Azure AI Speech Settings
    AZURE_SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY", "").strip()
    AZURE_SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION", "eastus").strip()

    # Azure OpenAI / Foundry Settings
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY", "").strip()
    AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").strip()
    AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-5-mini").strip()
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview").strip()

    # Fallback configuration
    ENABLE_FALLBACK_MODE = os.getenv("ENABLE_FALLBACK_MODE", "true").lower() in ("true", "1", "yes")

    @classmethod
    def is_azure_speech_configured(cls) -> bool:
        """Returns True if valid Azure Speech credentials are provided."""
        return bool(
            cls.AZURE_SPEECH_KEY
            and cls.AZURE_SPEECH_KEY != "your_azure_speech_key_here"
            and cls.AZURE_SPEECH_REGION
        )

    @classmethod
    def is_azure_openai_configured(cls) -> bool:
        """Returns True if valid Azure OpenAI / Foundry credentials are provided."""
        return bool(
            cls.AZURE_OPENAI_KEY
            and cls.AZURE_OPENAI_KEY != "your_azure_openai_key_here"
            and cls.AZURE_OPENAI_ENDPOINT
            and not cls.AZURE_OPENAI_ENDPOINT.startswith("https://your-resource-name")
        )

    @classmethod
    def get_system_mode(cls) -> dict:
        """Returns operational status for UI display and diagnostics."""
        speech_ok = cls.is_azure_speech_configured()
        openai_ok = cls.is_azure_openai_configured()
        return {
            "azure_speech": speech_ok,
            "azure_openai": openai_ok,
            "mode": "Azure Live" if (speech_ok and openai_ok) else ("Hybrid Azure" if (speech_ok or openai_ok) else "Intelligent Fallback"),
            "fallback_enabled": cls.ENABLE_FALLBACK_MODE,
        }
