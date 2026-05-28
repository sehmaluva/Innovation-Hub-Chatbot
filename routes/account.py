"""Account balance endpoints for the public API."""

from flask import Blueprint, jsonify

from routes.services import get_balance

account_bp = Blueprint("account", __name__)

@account_bp.route("/api/account/<phone_number>/balance", methods=["GET"])
def balance(phone_number: str):
    balance_info = get_balance(phone_number)
    return jsonify({"balance": balance_info})
