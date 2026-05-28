"""Price endpoints for the public API."""

from flask import Blueprint, jsonify

from routes.services import get_price, list_prices

prices_bp = Blueprint("prices", __name__)


@prices_bp.route("/api/prices/", methods=["GET"])
def prices() -> tuple:
    return jsonify({"prices": list_prices()})


@prices_bp.route("/api/prices/<symbol>", methods=["GET"])
def price(symbol: str):
    item = get_price(symbol)
    if not item:
        return jsonify({"error": "Instrument not found"}), 404
    return jsonify(item)
