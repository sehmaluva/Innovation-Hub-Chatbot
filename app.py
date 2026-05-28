import logging
import os
from logging.handlers import RotatingFileHandler

from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv

from routes.webhook import webhook_bp
from routes.prices import prices_bp
from routes.orders import orders_bp
from routes.portfolio import portfolio_bp
from routes.twilio_status import status_bp

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

file_handler = RotatingFileHandler("app.log", maxBytes=1_000_000, backupCount=3)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
logging.getLogger().addHandler(file_handler)

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})


@app.before_request
def log_request():
    app.logger.info(
        "Incoming request: %s %s from=%s",
        request.method,
        request.path,
        request.remote_addr,
    )


app.register_blueprint(webhook_bp)
app.register_blueprint(prices_bp)
app.register_blueprint(orders_bp)
app.register_blueprint(portfolio_bp)
app.register_blueprint(status_bp)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "innovation-hub-chatbot-starter"}), 200


if __name__ == "__main__":
    port_value = os.getenv("PORT") or "5000"
    port = int(port_value)
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
