import os
import re
from pathlib import Path
from config import Config

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SDK_AVAILABLE = True
except ImportError:
    AZURE_SDK_AVAILABLE = False


class SpeechService:
    """Handles Azure AI Speech services (Speech-to-Text & Text-to-Speech) with graceful fallbacks."""

    def __init__(self):
        self.is_configured = Config.is_azure_speech_configured() and AZURE_SDK_AVAILABLE
        self.speech_key = Config.AZURE_SPEECH_KEY
        self.speech_region = Config.AZURE_SPEECH_REGION

    def get_speech_config(self):
        """Builds Azure SpeechConfig instance if configured."""
        if not self.is_configured:
            return None
        speech_config = speechsdk.SpeechConfig(
            subscription=self.speech_key, region=self.speech_region
        )
        # Recommended default for natural conversational interview tone
        speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
        return speech_config

    def transcribe_audio_file(self, audio_file_path: str) -> dict:
        """
        Transcribes an audio file (WAV/WEBM) using Azure Speech SDK.
        Returns a dict: {'text': str, 'success': bool, 'engine': str, 'error': str|None}
        """
        if not os.path.exists(audio_file_path):
            return {
                "text": "",
                "success": False,
                "engine": "none",
                "error": f"Audio file not found: {audio_file_path}",
            }

        # Attempt Azure AI Speech recognition if configured
        if self.is_configured:
            try:
                speech_config = self.get_speech_config()
                audio_config = speechsdk.audio.AudioConfig(filename=audio_file_path)
                speech_recognizer = speechsdk.SpeechRecognizer(
                    speech_config=speech_config, audio_config=audio_config
                )

                result = speech_recognizer.recognize_once_async().get()

                if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                    return {
                        "text": result.text.strip(),
                        "success": True,
                        "engine": "Azure AI Speech",
                        "error": None,
                    }
                elif result.reason == speechsdk.ResultReason.NoMatch:
                    return {
                        "text": "",
                        "success": False,
                        "engine": "Azure AI Speech",
                        "error": "No speech detected in audio recording.",
                    }
                elif result.reason == speechsdk.ResultReason.Canceled:
                    cancellation = result.cancellation_details
                    return {
                        "text": "",
                        "success": False,
                        "engine": "Azure AI Speech",
                        "error": f"Speech recognition canceled: {cancellation.reason}. {cancellation.error_details}",
                    }
            except Exception as ex:
                print(f"[SpeechService] Azure Speech Error: {ex}")
                # Fallback on exception
                pass

        # Fallback Mode: For classroom demo / offline testing
        return {
            "text": "",
            "success": False,
            "engine": "Fallback Browser STT",
            "error": "Azure Speech not active or audio unrecognized. Falling back to browser speech.",
        }

    def synthesize_speech(self, text: str, output_path: str) -> bool:
        """
        Synthesizes question text to an audio file using Azure Text-to-Speech (JennyNeural).
        Returns True if successful, False otherwise.
        """
        if not self.is_configured:
            return False

        try:
            speech_config = self.get_speech_config()
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config, audio_config=audio_config
            )
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return True
            else:
                print(f"[SpeechService] Azure TTS Failed: {result.reason}")
                return False
        except Exception as ex:
            print(f"[SpeechService] Azure TTS Exception: {ex}")
            return False


# Singleton instance
speech_service = SpeechService()
