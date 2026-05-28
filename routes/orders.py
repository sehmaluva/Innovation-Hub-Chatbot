"""Order endpoints for the public API."""

from flask import Blueprint, jsonify, request

from routes.services import get_order_history, place_order

orders_bp = Blueprint("orders", __name__)


@orders_bp.route("/api/orders/", methods=["POST"])
def create_order():
    payload = request.get_json(silent=True) or {}
    phone_number = payload.get("phone_number", "")
    symbol = payload.get("symbol")
    order_type = payload.get("order_type", "")
    quantity = payload.get("quantity")

    result = place_order(phone_number, symbol, order_type, quantity)
    status_code = 200 if result.get("ok") else 400
    return jsonify(result), status_code


@orders_bp.route("/api/orders/<phone_number>", methods=["GET"])
def order_history(phone_number: str):
    limit = request.args.get("limit", default=10, type=int)
    return jsonify({"orders": get_order_history(phone_number, limit=limit)})
