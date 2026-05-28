"""Portfolio endpoint for the public API."""

from flask import Blueprint, jsonify

from routes.services import get_portfolio

portfolio_bp = Blueprint("portfolio", __name__)


@portfolio_bp.route("/api/portfolio/<phone_number>", methods=["GET"])
def portfolio(phone_number: str):
    holdings = get_portfolio(phone_number)
    return jsonify({"portfolio": holdings})
