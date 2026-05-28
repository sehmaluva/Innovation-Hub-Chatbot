"""Speech-to-text helpers for WhatsApp voice notes."""

from __future__ import annotations

import base64
import json
import logging
import mimetypes
import os
import urllib.error
import urllib.parse
import urllib.request

logger = logging.getLogger(__name__)


def _build_multipart_form_data(
    fields: dict[str, str],
    file_field_name: str,
    file_name: str,
    file_bytes: bytes,
    file_content_type: str,
) -> tuple[bytes, str]:
    boundary = "----InnovationHubVoiceBoundary"
    lines: list[bytes] = []

    for field_name, field_value in fields.items():
        lines.extend(
            [
                f"--{boundary}".encode("utf-8"),
                f'Content-Disposition: form-data; name="{field_name}"'.encode("utf-8"),
                b"",
                field_value.encode("utf-8"),
            ]
        )

    lines.extend(
        [
            f"--{boundary}".encode("utf-8"),
            f'Content-Disposition: form-data; name="{file_field_name}"; filename="{file_name}"'.encode(
                "utf-8"
            ),
            f"Content-Type: {file_content_type}".encode("utf-8"),
            b"",
        ]
    )
    lines.append(file_bytes)
    lines.extend([f"--{boundary}--".encode("utf-8"), b""])

    body = b"\r\n".join(lines)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


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
    """Download a Twilio media URL and transcribe it with OpenAI's audio API."""

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()

    if not api_key:
        logger.warning("OPENAI_API_KEY is not configured; voice commands are disabled.")
        return ""

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

    audio_extension = _guess_audio_extension(content_type)
    file_name = f"voice_note.{audio_extension}"

    multipart_body, multipart_type = _build_multipart_form_data(
        fields={
            "model": os.getenv("OPENAI_TRANSCRIPTION_MODEL", "whisper-1"),
            "language": os.getenv("OPENAI_TRANSCRIPTION_LANGUAGE", "en"),
            "prompt": "Innovation Hub WhatsApp trading bot. ZANACO ZCCM ZSUG PUMA NANGA BATA PRIMA LAFARGE.",
        },
        file_field_name="file",
        file_name=file_name,
        file_bytes=audio_bytes,
        file_content_type=content_type,
    )

    transcript_request = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=multipart_body,
        method="POST",
    )
    transcript_request.add_header("Authorization", f"Bearer {api_key}")
    transcript_request.add_header("Content-Type", multipart_type)

    try:
        with urllib.request.urlopen(
            transcript_request, timeout=60
        ) as transcript_response:
            payload = json.loads(transcript_response.read().decode("utf-8"))
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
    ) as exc:
        logger.exception("Voice transcription failed: %s", exc)
        return ""

    text = str(payload.get("text", "")).strip()
    return text
