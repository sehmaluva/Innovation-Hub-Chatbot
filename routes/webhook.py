"""Twilio webhook for incoming WhatsApp messages."""

import logging
import os

from flask import Blueprint, Response, request
from twilio.twiml.messaging_response import MessagingResponse

from routes.services import build_reply
from routes.speech_to_text import transcribe_voice_note

webhook_bp = Blueprint("webhook", __name__)
logger = logging.getLogger(__name__)


@webhook_bp.route("/webhook", methods=["POST"])
def webhook() -> Response:
    phone_number = request.form.get("From", "")
    text = request.form.get("Body", "").strip()
    num_media = int(request.form.get("NumMedia", "0") or 0)
    media_url = request.form.get("MediaUrl0", "").strip()
    media_content_type = request.form.get("MediaContentType0", "").strip().lower()

    logger.info(
        "Webhook payload received: from=%s body=%s num_media=%s media_type=%s",
        phone_number,
        text,
        num_media,
        media_content_type,
    )

    if num_media > 0 and media_url and "audio" in media_content_type:
        text = transcribe_voice_note(media_url)
        if not text:
            reply_text = "I could not transcribe that voice note. Please try again or send the command as text."
            twiml = MessagingResponse()
            twiml.message(reply_text)
            return Response(str(twiml), mimetype="application/xml")

    if not text:
        reply_text = "Please send a message such as: show prices, price of ZANACO, buy 100 ZSUG, my portfolio, or my orders."
    else:
        reply_text = build_reply(phone_number, text)

    twiml = MessagingResponse()
    message = twiml.message(reply_text)

    status_callback_url = os.getenv("TWILIO_STATUS_CALLBACK_URL")
    if status_callback_url:
        # Twilio will POST delivery updates for the outbound reply message here.
        message.status_callback = status_callback_url
        logger.info("Attached Twilio status callback: %s", status_callback_url)
    else:
        logger.warning(
            "TWILIO_STATUS_CALLBACK_URL is not set; Twilio delivery callbacks will not be sent"
        )

    return Response(str(twiml), mimetype="application/xml")
