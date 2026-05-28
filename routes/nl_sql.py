"""NL to SQL Generation endpoint (Generate Only Prototype)."""

import os
import json
from flask import Blueprint, jsonify, request

nl_sql_bp = Blueprint("nl_sql", __name__)

SCHEMA_CONTEXT = """
The database has the following tables:
- Users (user_id, phone_number, full_name, email, is_active, cash_balance, created_at, updated_at)
- Instruments (instrument_id, symbol, name, sector, currency, is_active, created_at)
- Prices (price_id, instrument_id, bid_price, ask_price, last_price, change_pct, volume, recorded_at)
- Orders (order_id, user_id, instrument_id, order_type, quantity, limit_price, executed_price, status, notes, placed_at, executed_at, cancelled_at)
- Portfolio (portfolio_id, user_id, instrument_id, quantity, avg_cost, total_invested, updated_at)

Write a valid T-SQL (MSSQL) query to answer the user's natural language request.
Return strictly only the raw SQL query. Do not use formatting like ```sql...```.
Only use SELECT operations. Do not include DML like INSERT, UPDATE, DELETE.
"""

@nl_sql_bp.route("/api/sql/generate", methods=["POST"])
def generate_sql():
    # Only load openai if required
    try:
        from openai import OpenAI
    except ImportError:
        return jsonify({"error": "OpenAI library is not installed"}), 500

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return jsonify({"error": "OPENAI_API_KEY is missing"}), 500

    payload = request.get_json(silent=True) or {}
    nl_query = payload.get("query", "").strip()

    if not nl_query:
        return jsonify({"error": "No query provided"}), 400

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": SCHEMA_CONTEXT},
                {"role": "user", "content": nl_query}
            ],
            temperature=0,
            max_tokens=250
        )
        sql = response.choices[0].message.content.strip()
        
        # Simple safety check 
        forbidden_keywords = {"insert", "update", "delete", "drop", "truncate", "alter", "exec", "execute"}
        sql_lower = sql.lower()
        if any(keyword in sql_lower for keyword in forbidden_keywords):
            return jsonify({"error": "Generated SQL contains forbidden keywords", "sql": sql}), 400

        return jsonify({"sql": sql}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
