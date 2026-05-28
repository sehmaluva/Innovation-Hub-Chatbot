"""Speech-to-text helpers for WhatsApp voice notes."""

from __future__ import annotations

import base64
import logging
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def _guess_audio_extension(content_type: str | None) -> str:
    if not content_type:
        return "ogg"
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
    if guessed:
        return guessed.lstrip(".")
    if "ogg" in content_type:
        return "ogg"
    if "mp4" in content_type or "m4a" in content_type:
        return "m4a"
    if "wav" in content_type:
        return "wav"
    if "mpeg" in content_type or "mp3" in content_type:
        return "mp3"
    return "ogg"


def transcribe_voice_note(media_url: str) -> str:
    """Download a Twilio media URL and transcribe it with Google Gemini."""

    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    model = os.getenv("GEMINI_MODEL", "").strip()

    if not gemini_key:
        logger.warning("GEMINI_API_KEY is not configured; voice commands are disabled.")
        return ""

    if not model:
        logger.warning(
            "GEMINI_MODEL is not configured; defaulting to gemini-2.5-flash."
        )
        model = "gemini-2.5-flash"

    if not account_sid or not auth_token:
        logger.warning(
            "Twilio credentials are missing; cannot download voice note media."
        )
        return ""

    media_request = urllib.request.Request(media_url)
    encoded_credentials = base64.b64encode(
        f"{account_sid}:{auth_token}".encode("utf-8")
    ).decode("ascii")
    media_request.add_header("Authorization", f"Basic {encoded_credentials}")

    try:
        with urllib.request.urlopen(media_request, timeout=30) as media_response:
            audio_bytes = media_response.read()
            content_type = media_response.headers.get_content_type() or "audio/ogg"
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        logger.exception("Failed to download Twilio voice note: %s", exc)
        return ""

    try:
        client = genai.Client(api_key=gemini_key)
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type=content_type,
                ),
                "Transcribe this audio precisely. Return nothing but the transcription.",
            ],
        )
        text = response.text.strip() if response.text else ""
        return text
    except Exception as exc:
        logger.exception("Voice transcription completely failed: %s", exc)
        return ""
