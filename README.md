# WhatsApp Trading Bot — Starter Code

A working WhatsApp chatbot built with **Flask + Twilio + MSSQL**.

Users interact via a simple numbered menu or direct commands:

```
Reply with:
1 - View all prices
2 - View my portfolio
3 - My order history

BUY 100 ZANACO   — place a buy order
SELL 50 ZCCM     — place a sell order
```

---

## Project structure

```
challenge-starter/
├── app.py                      # Flask entry point
├── requirements.txt
├── .env.example
│
├── database/
│   ├── schema.sql              # Tables: Users, Instruments, Prices, Orders, Portfolio
│   ├── seed_data.sql           # Sample instruments, prices, demo users
│   └── stored_procedures.sql  # sp_GetAllPrices, sp_PlaceOrder, sp_GetPortfolio, ...
│
├── models/
│   └── db.py                   # MSSQL connection helper
│
└── routes/
    ├── webhook.py              # POST /webhook  — Twilio inbound handler
    ├── prices.py               # GET  /api/prices/, /api/prices/<symbol>
    ├── orders.py               # POST /api/orders/, GET /api/orders/<phone>
    └── portfolio.py            # GET  /api/portfolio/<phone>
```

---

## API endpoints

| Method | URL | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/prices/` | All instrument prices |
| GET | `/api/prices/<symbol>` | Single instrument price |
| POST | `/api/orders/` | Place a BUY or SELL order |
| GET | `/api/orders/<phone>` | Order history for a user |
| GET | `/api/portfolio/<phone>` | Holdings and P&L for a user |
| POST | `/webhook` | Twilio WhatsApp webhook |

---

## Quick start

```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # fill in your credentials
python app.py
```

Database setup (SQL Server — run in order):

```
database/schema.sql
database/seed_data.sql
database/stored_procedures.sql
```

See [CHALLENGE.md](CHALLENGE.md) for the full challenge brief.
