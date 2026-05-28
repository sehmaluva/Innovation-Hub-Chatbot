"""Shared data access, parsing, and formatting helpers for the Flask app."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from typing import Any

import pyodbc


def _clean_text(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", text.upper()).strip()


Cursor = pyodbc.Cursor


INSTRUMENTS = [
    ("ZANACO", "Zambia National Commercial Bank"),
    ("ZCCM", "ZCCM Investments Holdings"),
    ("ZSUG", "Zambia Sugar"),
    ("PUMA", "Puma Energy Zambia"),
    ("NANGA", "Nanga Farms"),
    ("BATA", "Bata Shoes"),
    ("PRIMA", "Prima Reinsurance"),
    ("LAFARGE", "Lafarge Zambia"),
]

HELP_TEXT = (
    "I can help with:\n"
    "1 - View all prices\n"
    "2 - View my portfolio\n"
    "3 - View my order history\n\n"
    "You can also type things like:\n"
    "- show prices\n"
    "- price of ZANACO\n"
    "- buy 100 ZSUG\n"
    "- sell 50 ZCCM\n"
    "- what do I own?"
)

_ALIAS_LOOKUP: dict[str, str] = {}
for instrument_code, name in INSTRUMENTS:
    _ALIAS_LOOKUP[_clean_text(instrument_code)] = instrument_code
    _ALIAS_LOOKUP[_clean_text(name)] = instrument_code

_ALIAS_PATTERNS = sorted(
    _ALIAS_LOOKUP.items(), key=lambda item: len(item[0]), reverse=True
)

_PRICE_ALL_TRIGGERS = (
    "show prices",
    "view prices",
    "all prices",
    "market today",
    "what's trading",
    "whats trading",
    "what is trading",
    "trading today",
    "show market",
    "market prices",
    "prices",
)

_PORTFOLIO_TRIGGERS = (
    "portfolio",
    "holdings",
    "what do i own",
    "what do i have",
    "my stocks",
    "my shares",
    "show my holdings",
)

_HISTORY_TRIGGERS = (
    "orders",
    "order history",
    "recent transactions",
    "transactions",
    "transaction history",
    "my orders",
    "past orders",
    "trades",
)

_BUY_TRIGGERS = (
    "buy",
    "purchase",
    "invest in",
    "i want",
    "get me",
    "add",
)

_SELL_TRIGGERS = (
    "sell",
    "offload",
    "dispose",
    "liquidate",
    "dump",
)

_BALANCE_TRIGGERS = (
    "balance",
    "cash",
    "how much money",
    "funds",
)

_PRICE_SINGLE_TRIGGERS = (
    "price of",
    "price for",
    "how much is",
    "how much for",
    "what is the price of",
    "quote for",
    "show price of",
)


def normalize_phone(phone_number: str | None) -> str:
    if not phone_number:
        return ""
    return phone_number.replace("whatsapp:", "", 1).strip()


@contextmanager
def get_connection():
    # Support both environment variable names: MSSQL_ODBC_DRIVER (preferred)
    # and MSSQL_DRIVER (legacy). Default to ODBC Driver 18 which supports
    # modern SQL Server versions.
    driver = (
        os.getenv("MSSQL_ODBC_DRIVER")
        or os.getenv("MSSQL_DRIVER")
        or "ODBC Driver 18 for SQL Server"
    )
    server = os.getenv("MSSQL_SERVER")
    database = os.getenv("MSSQL_DATABASE")
    username = os.getenv("MSSQL_USERNAME")
    password = os.getenv("MSSQL_PASSWORD")

    if not server or not database or not username or not password:
        raise RuntimeError(
            "Missing MSSQL connection settings. Set MSSQL_SERVER, MSSQL_DATABASE, "
            "MSSQL_USERNAME, and MSSQL_PASSWORD."
        )

    conn_str = (
        f"DRIVER={{{driver}}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        "Encrypt=yes;TrustServerCertificate=yes;"
    )
    connection = pyodbc.connect(conn_str)
    cursor: Cursor = connection.cursor()
    try:
        yield connection, cursor
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def _fetch_user_id(cursor: Cursor, phone_number: str) -> int | None:
    cursor.execute(
        "SELECT user_id FROM dbo.Users WHERE phone_number = ? AND is_active = 1",
        (phone_number,),
    )
    row = cursor.fetchone()
    return int(row[0]) if row else None


def _get_or_create_user_id(cursor: Cursor, phone_number: str) -> int:
    user_id = _fetch_user_id(cursor, phone_number)
    if user_id is not None:
        return user_id

    cursor.execute(
        "INSERT INTO dbo.Users (phone_number, full_name, email) VALUES (?, ?, ?)",
        (phone_number, "WhatsApp Investor", None),
    )
    cursor.execute("SELECT CAST(SCOPE_IDENTITY() AS INT)")
    row = cursor.fetchone()
    if not row:
        raise RuntimeError("Could not read the inserted user ID from SQL Server.")
    return int(row[0])

def get_balance(phone_number: str) -> float | None:
    normalized = normalize_phone(phone_number)
    with get_connection() as (_, cursor):
        cursor.execute(
            "SELECT cash_balance FROM dbo.Users WHERE phone_number = ? AND is_active = 1",
            (normalized,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        return float(row[0])


def _fetch_instrument(cursor: Cursor, ticker_code: str) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT instrument_id, symbol, name, currency
        FROM dbo.Instruments
        WHERE symbol = ? AND is_active = 1
        """,
        (ticker_code,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "instrument_id": int(row[0]),
        "symbol": row[1],
        "name": row[2],
        "currency": row[3],
    }


def _fetch_latest_price(cursor: Cursor, instrument_id: int) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT TOP 1 bid_price, ask_price, last_price, change_pct, volume, recorded_at
        FROM dbo.Prices
        WHERE instrument_id = ?
        ORDER BY recorded_at DESC
        """,
        (instrument_id,),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "bid_price": float(row[0]),
        "ask_price": float(row[1]),
        "last_price": float(row[2]),
        "change_pct": float(row[3]),
        "volume": int(row[4]),
        "recorded_at": row[5],
    }


def _fetch_holding(
    cursor: Cursor, user_id: int, instrument_id: int
) -> dict[str, Any] | None:
    cursor.execute(
        """
        SELECT portfolio_id, quantity, avg_cost
        FROM dbo.Portfolio
        WHERE user_id = ? AND instrument_id = ?
        """,
        (user_id, instrument_id),
    )
    row = cursor.fetchone()
    if not row:
        return None
    return {
        "portfolio_id": int(row[0]),
        "quantity": int(row[1]),
        "avg_cost": float(row[2]),
    }


def _upsert_holding(
    cursor: Cursor, user_id: int, instrument_id: int, quantity_delta: int, price: float
) -> dict[str, Any]:
    holding = _fetch_holding(cursor, user_id, instrument_id)

    if holding is None:
        cursor.execute(
            """
            INSERT INTO dbo.Portfolio (user_id, instrument_id, quantity, avg_cost, total_invested)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, instrument_id, quantity_delta, price, quantity_delta * price),
        )
        return {"quantity": quantity_delta, "avg_cost": price}

    new_quantity = holding["quantity"] + quantity_delta
    if new_quantity <= 0:
        cursor.execute(
            "DELETE FROM dbo.Portfolio WHERE portfolio_id = ?",
            (holding["portfolio_id"],),
        )
        return {"quantity": 0, "avg_cost": holding["avg_cost"]}

    if quantity_delta > 0:
        old_value = holding["quantity"] * holding["avg_cost"]
        new_value = quantity_delta * price
        new_avg_cost = (old_value + new_value) / new_quantity
    else:
        new_avg_cost = holding["avg_cost"]

    cursor.execute(
        """
        UPDATE dbo.Portfolio
        SET quantity = ?, avg_cost = ?, total_invested = ?, updated_at = SYSUTCDATETIME()
        WHERE portfolio_id = ?
        """,
        (
            new_quantity,
            new_avg_cost,
            new_quantity * new_avg_cost,
            holding["portfolio_id"],
        ),
    )
    return {"quantity": new_quantity, "avg_cost": new_avg_cost}


def normalize_symbol(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = _clean_text(value)
    if not cleaned:
        return None

    if cleaned in _ALIAS_LOOKUP:
        return _ALIAS_LOOKUP[cleaned]

    compact = cleaned.replace(" ", "")
    for alias_code, ticker_code in _ALIAS_PATTERNS:
        if alias_code in cleaned or alias_code.replace(" ", "") == compact:
            return ticker_code

    return cleaned.split()[0]


def extract_symbol(text: str) -> str | None:
    cleaned = _clean_text(text)
    for alias_code, ticker_code in _ALIAS_PATTERNS:
        pattern = rf"\b{re.escape(alias_code)}\b"
        if re.search(pattern, cleaned):
            return ticker_code
    return None


def extract_quantity(text: str) -> int | None:
    match = re.search(r"\b(\d[\d,]*)\b", text)
    if not match:
        return None
    return int(match.group(1).replace(",", ""))


def extract_limit(text: str) -> int | None:
    match = re.search(r"(?:last|recent|show me the last)\s+(\d+)\b", _clean_text(text))
    if match:
        return int(match.group(1))
    return None


def extract_date_range(text: str) -> str | None:
    cleaned = _clean_text(text)
    if "TODAY" in cleaned:
        return "today"
    if "THIS WEEK" in cleaned or "WEEK" in cleaned:
        return "this_week"
    if "THIS MONTH" in cleaned or "MONTH" in cleaned:
        return "this_month"
    return None


def _contains_any(cleaned_text: str, phrases: tuple[str, ...]) -> bool:
    return any(_clean_text(phrase) in cleaned_text for phrase in phrases)


def parse_message(text: str) -> dict[str, Any]:
    cleaned = _clean_text(text)
    if not cleaned:
        return {"intent": "help"}

    if cleaned in {"1", "2", "3"}:
        return {
            "1": {"intent": "prices"},
            "2": {"intent": "portfolio"},
            "3": {"intent": "history"},
        }[cleaned]

    if cleaned in {"HELP", "MENU", "START", "COMMANDS"}:
        return {"intent": "help"}

    if _contains_any(cleaned, _PORTFOLIO_TRIGGERS):
        return {"intent": "portfolio"}

    if _contains_any(cleaned, _BALANCE_TRIGGERS):
        return {"intent": "balance"}

    if _contains_any(cleaned, _HISTORY_TRIGGERS):
        return {
            "intent": "history",
            "limit": extract_limit(text) or 10,
            "date_range": extract_date_range(text),
        }

    ticker_code = extract_symbol(text)

    if _contains_any(cleaned, _BUY_TRIGGERS):
        return {
            "intent": "buy",
            "symbol": ticker_code,
            "quantity": extract_quantity(text),
        }

    if _contains_any(cleaned, _SELL_TRIGGERS):
        return {
            "intent": "sell",
            "symbol": ticker_code,
            "quantity": extract_quantity(text),
        }

    if ticker_code and _contains_any(cleaned, _PRICE_SINGLE_TRIGGERS + ("HOW MUCH",)):
        return {"intent": "price", "symbol": ticker_code}

    if _contains_any(cleaned, _PRICE_ALL_TRIGGERS):
        return {"intent": "prices"}

    if ticker_code and ("PRICE" in cleaned or "HOW MUCH" in cleaned):
        return {"intent": "price", "symbol": ticker_code}

    return {"intent": "help"}


def list_prices() -> list[dict[str, Any]]:
    with get_connection() as (_, cursor):
        cursor.execute(
            """
            WITH latest_prices AS (
                SELECT
                    instrument_id,
                    bid_price,
                    ask_price,
                    last_price,
                    change_pct,
                    volume,
                    recorded_at,
                    ROW_NUMBER() OVER (PARTITION BY instrument_id ORDER BY recorded_at DESC) AS rn
                FROM dbo.Prices
            )
            SELECT
                i.symbol,
                i.name,
                i.currency,
                p.bid_price,
                p.ask_price,
                p.last_price,
                p.change_pct,
                p.volume,
                p.recorded_at
            FROM dbo.Instruments i
            JOIN latest_prices p ON p.instrument_id = i.instrument_id AND p.rn = 1
            WHERE i.is_active = 1
            ORDER BY i.symbol
            """,
        )
        rows = cursor.fetchall()
        return [
            {
                "symbol": row[0],
                "name": row[1],
                "currency": row[2],
                "bid_price": float(row[3]),
                "ask_price": float(row[4]),
                "last_price": float(row[5]),
                "change_pct": float(row[6]),
                "volume": int(row[7]),
                "recorded_at": row[8],
            }
            for row in rows
        ]


def get_price(ticker_code: str) -> dict[str, Any] | None:
    normalized = normalize_symbol(ticker_code)
    if not normalized:
        return None

    with get_connection() as (_, cursor):
        instrument = _fetch_instrument(cursor, normalized)
        if not instrument:
            return None
        latest_price = _fetch_latest_price(cursor, instrument["instrument_id"])
        if not latest_price:
            return None
        return {**instrument, **latest_price}


def get_portfolio(phone_number: str) -> list[dict[str, Any]]:
    normalized_phone = normalize_phone(phone_number)
    with get_connection() as (_, cursor):
        cursor.execute(
            "SELECT user_id FROM dbo.Users WHERE phone_number = ? AND is_active = 1",
            (normalized_phone,),
        )
        row = cursor.fetchone()
        if not row:
            return []
        user_id = int(row[0])
        cursor.execute(
            """
            SELECT
                i.symbol,
                i.name,
                i.currency,
                pf.quantity,
                pf.avg_cost,
                p.last_price,
                (p.last_price - pf.avg_cost) * pf.quantity AS unrealised_pnl,
                CASE
                    WHEN pf.avg_cost > 0 THEN ROUND(((p.last_price - pf.avg_cost) / pf.avg_cost) * 100, 2)
                    ELSE 0
                END AS return_pct
            FROM dbo.Portfolio pf
            JOIN dbo.Instruments i ON i.instrument_id = pf.instrument_id
            CROSS APPLY (
                SELECT TOP 1 last_price
                FROM dbo.Prices px
                WHERE px.instrument_id = pf.instrument_id
                ORDER BY px.recorded_at DESC
            ) p
            WHERE pf.user_id = ? AND pf.quantity > 0
            ORDER BY i.symbol
            """,
            (user_id,),
        )
        rows = cursor.fetchall()
        return [
            {
                "symbol": row[0],
                "name": row[1],
                "currency": row[2],
                "quantity": int(row[3]),
                "avg_cost": float(row[4]),
                "last_price": float(row[5]),
                "unrealised_pnl": float(row[6]),
                "return_pct": float(row[7]),
            }
            for row in rows
        ]


def get_order_history(phone_number: str, limit: int = 10) -> list[dict[str, Any]]:
    normalized_phone = normalize_phone(phone_number)
    with get_connection() as (_, cursor):
        cursor.execute(
            "SELECT user_id FROM dbo.Users WHERE phone_number = ? AND is_active = 1",
            (normalized_phone,),
        )
        row = cursor.fetchone()
        if not row:
            return []
        user_id = int(row[0])
        cursor.execute(
            """
            SELECT TOP (?)
                o.order_id,
                i.symbol,
                i.name,
                o.order_type,
                o.quantity,
                o.limit_price,
                o.executed_price,
                o.status,
                o.placed_at,
                o.executed_at
            FROM dbo.Orders o
            JOIN dbo.Instruments i ON i.instrument_id = o.instrument_id
            WHERE o.user_id = ?
            ORDER BY o.placed_at DESC, o.order_id DESC
            """,
            (limit, user_id),
        )
        rows = cursor.fetchall()
        return [
            {
                "order_id": int(row[0]),
                "symbol": row[1],
                "name": row[2],
                "order_type": row[3],
                "quantity": int(row[4]),
                "limit_price": float(row[5]) if row[5] is not None else None,
                "executed_price": float(row[6]) if row[6] is not None else None,
                "status": row[7],
                "placed_at": row[8],
                "executed_at": row[9],
            }
            for row in rows
        ]


def place_order(
    phone_number: str,
    ticker_code: str | None,
    order_type: str | None,
    quantity: int | str | None,
) -> dict[str, Any]:
    normalized_phone = normalize_phone(phone_number)
    normalized_symbol = normalize_symbol(ticker_code)
    order_type = (order_type or "").upper().strip()

    if isinstance(quantity, str):
        quantity = quantity.strip()
        quantity = int(quantity) if quantity.isdigit() else None

    if order_type not in {"BUY", "SELL"}:
        return {"ok": False, "message": "Unsupported order type. Use BUY or SELL."}

    if not normalized_symbol:
        action = "buy" if order_type == "BUY" else "sell"
        return {
            "ok": False,
            "message": f"Which stock would you like to {action}? Try: {action} 100 ZANACO",
        }

    if not quantity or quantity <= 0:
        action = "buy" if order_type == "BUY" else "sell"
        return {
            "ok": False,
            "message": f"How many shares of {normalized_symbol} would you like to {action}?",
        }

    with get_connection() as (_, cursor):
        user_id = _get_or_create_user_id(cursor, normalized_phone)
        instrument = _fetch_instrument(cursor, normalized_symbol)
        if not instrument:
            return {
                "ok": False,
                "message": f"Instrument {normalized_symbol} was not found.",
            }

        latest_price = _fetch_latest_price(cursor, instrument["instrument_id"])
        if not latest_price:
            return {
                "ok": False,
                "message": f"No market price is available for {normalized_symbol} right now.",
            }

        current_price = latest_price["last_price"]
        holding = _fetch_holding(cursor, user_id, instrument["instrument_id"])
        
        # Check cash balance for BUY
        cursor.execute("SELECT cash_balance FROM dbo.Users WHERE user_id = ?", (user_id,))
        cash_row = cursor.fetchone()
        cash_balance = float(cash_row[0]) if cash_row else 0.0
        
        total_value = current_price * quantity

        if order_type == "BUY":
            if cash_balance < total_value:
                return {
                    "ok": False,
                    "message": f"Insufficient funds. This order costs {format_money(total_value)}, but you only have {format_money(cash_balance)}."
                }

        if order_type == "SELL":
            owned = holding["quantity"] if holding else 0
            if owned < quantity:
                return {
                    "ok": False,
                    "message": (
                        f"You only hold {owned} shares of {normalized_symbol}. "
                        f"You cannot sell {quantity}."
                    ),
                }

        updated_holding = _upsert_holding(
            cursor,
            user_id,
            instrument["instrument_id"],
            quantity if order_type == "BUY" else -quantity,
            current_price,
        )

        cursor.execute(
            """
            INSERT INTO dbo.Orders (
                user_id, instrument_id, order_type, quantity,
                limit_price, executed_price, status, executed_at
            )
            OUTPUT INSERTED.order_id
            VALUES (?, ?, ?, ?, ?, ?, 'EXECUTED', SYSUTCDATETIME())
            """,
            (
                user_id,
                instrument["instrument_id"],
                order_type,
                quantity,
                current_price,
                current_price,
            ),
        )
        row = cursor.fetchone()
        if not row or row[0] is None:
            return {
                "ok": False,
                "message": "The order was saved, but I could not read the new order ID. Please check the database and try again.",
            }
        order_id = int(row[0])

        # Update cash balance
        new_cash_balance = cash_balance - total_value if order_type == "BUY" else cash_balance + total_value
        cursor.execute("UPDATE dbo.Users SET cash_balance = ? WHERE user_id = ?", (new_cash_balance, user_id))

    remaining = updated_holding["quantity"]
    average_cost = updated_holding["avg_cost"]

    if order_type == "BUY":
        message = (
            f"Buy order placed for {quantity} shares of {normalized_symbol} at {format_money(current_price)}. "
            f"Order #{order_id}. New holding: {remaining} shares at an average cost of {format_money(average_cost)}."
        )
    else:
        message = (
            f"Sell order placed for {quantity} shares of {normalized_symbol} at {format_money(current_price)}. "
            f"Order #{order_id}. Remaining holding: {remaining} shares. Proceeds: {format_money(total_value)}."
        )

    return {
        "ok": True,
        "message": message,
        "order_id": order_id,
        "symbol": normalized_symbol,
        "order_type": order_type,
        "quantity": quantity,
        "price": current_price,
        "total_value": total_value,
    }


def format_money(value: float, currency: str = "ZMW") -> str:
    return f"{currency} {value:,.2f}"


def format_prices_text(prices: list[dict[str, Any]]) -> str:
    if not prices:
        return "No market prices are available right now."

    lines = ["Market prices:"]
    for item in prices:
        lines.append(
            f"- {item['symbol']}: {format_money(item['last_price'], item['currency'])} "
            f"({item['name']})"
        )
    return "\n".join(lines)


def format_price_text(price: dict[str, Any]) -> str:
    return (
        f"{price['symbol']} - {price['name']}\n"
        f"Last price: {format_money(price['last_price'], price['currency'])}\n"
        f"Bid: {format_money(price['bid_price'], price['currency'])}\n"
        f"Ask: {format_money(price['ask_price'], price['currency'])}\n"
        f"Change: {price['change_pct']:+.2f}%\n"
        f"Volume: {price['volume']:,}"
    )


def format_portfolio_text(holdings: list[dict[str, Any]]) -> str:
    if not holdings:
        return "Your portfolio is empty right now."

    lines = ["Your portfolio:"]
    total_value = 0.0
    total_cost = 0.0

    for holding in holdings:
        market_value = holding["quantity"] * holding["last_price"]
        cost_basis = holding["quantity"] * holding["avg_cost"]
        pnl = market_value - cost_basis
        pnl_pct = (pnl / cost_basis * 100) if cost_basis else 0.0
        total_value += market_value
        total_cost += cost_basis
        lines.append(
            f"- {holding['symbol']}: {holding['quantity']} shares @ {format_money(holding['last_price'], holding['currency'])} "
            f"| Value {format_money(market_value, holding['currency'])} | P/L {pnl:+.2f} ({pnl_pct:+.2f}%)"
        )

    total_pnl = total_value - total_cost
    total_pct = (total_pnl / total_cost * 100) if total_cost else 0.0
    lines.append(
        f"Total value: {format_money(total_value)} | Total P/L: {total_pnl:+.2f} ({total_pct:+.2f}%)"
    )
    return "\n".join(lines)


def format_history_text(orders: list[dict[str, Any]], limit: int = 10) -> str:
    if not orders:
        return "No order history found."

    lines = [f"Order history (last {min(limit, len(orders))}):"]
    for order in orders:
        lines.append(
            f"- #{order['order_id']} {order['order_type']} {order['quantity']} {order['symbol']} "
            f"at {format_money(order['executed_price'] or order['limit_price'] or 0.0)} "
            f"| {order['status']}"
        )
    return "\n".join(lines)


def build_reply(phone_number: str, text: str) -> str:
    parsed = parse_message(text)
    intent = parsed.get("intent", "help")

    if intent == "help":
        return HELP_TEXT

    if intent == "prices":
        return format_prices_text(list_prices())

    if intent == "price":
        symbol = parsed.get("symbol")
        if not isinstance(symbol, str):
            return "I could not find that instrument. Try one of: ZANACO, ZCCM, ZSUG, PUMA, NANGA, BATA, PRIMA, LAFARGE."
        price = get_price(symbol)
        if not price:
            return "I could not find that instrument. Try one of: ZANACO, ZCCM, ZSUG, PUMA, NANGA, BATA, PRIMA, LAFARGE."
        return format_price_text(price)

    if intent == "portfolio":
        return format_portfolio_text(get_portfolio(phone_number))

    if intent == "balance":
        balance = get_balance(phone_number)
        if balance is None:
            return "I could not find your account. Please check your phone number registration."
        return f"Your current cash balance is {format_money(balance)}."

    if intent == "history":
        limit = parsed.get("limit") or 10
        return format_history_text(
            get_order_history(phone_number, limit=limit), limit=limit
        )

    if intent in {"buy", "sell"}:
        result = place_order(
            phone_number,
            parsed.get("symbol"),
            intent,
            parsed.get("quantity"),
        )
        return result["message"]

    return HELP_TEXT
