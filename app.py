import logging
import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

from routes.webhook import webhook_bp
from routes.prices import prices_bp
from routes.orders import orders_bp
from routes.portfolio import portfolio_bp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

app.register_blueprint(webhook_bp)
app.register_blueprint(prices_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(portfolio_bp)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "innovation-hub-chatbot-starter"}), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
