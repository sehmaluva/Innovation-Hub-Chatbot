"""Endpoint to receive Twilio status callbacks for outgoing messages."""

import logging

from flask import Blueprint, request, jsonify

status_bp = Blueprint("twilio_status", __name__)
logger = logging.getLogger(__name__)


@status_bp.route("/twilio-status", methods=["POST"])
def twilio_status():
    # Twilio will POST fields like MessageSid, MessageStatus, To, From, ErrorCode, ErrorMessage
    payload = request.form.to_dict()
    # Log at warning level so it is visible even if app logger defaults are restrictive.
    logger.warning("Twilio status callback received: %s", payload)
    print(f"Twilio status callback received: {payload}")
    # Optionally, you could persist these to a database or update order state
    return ("", 200)
