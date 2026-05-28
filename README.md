# Innovation Hub Chatbot

WhatsApp-based trading assistant built with Flask, Twilio, and SQL Server.

This README focuses on:
1. How to run the system locally
2. How the system works end to end

## What This App Does

Users send WhatsApp messages such as:
- 1 (show all prices)
- 2 (show portfolio)
- 3 (show order history)
- buy 100 ZANACO
- sell 50 ZCCM
- price of ZSUG

The app parses intent, reads/writes data in SQL Server, and responds through Twilio.

## Prerequisites

Install these first:
1. Python 3.10+
2. SQL Server (local or remote)
3. ODBC Driver 18 for SQL Server
4. A Twilio account with WhatsApp Sandbox or a WhatsApp-enabled number
5. Optional: ngrok (for exposing local webhook URLs)

## 1) Environment Setup

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create a .env file in the project root with at least the following keys:

```dotenv
MSSQL_SERVER=127.0.0.1
MSSQL_PORT=1433
MSSQL_DATABASE=Chatbot
MSSQL_USERNAME=sa
MSSQL_PASSWORD=your_password
MSSQL_ODBC_DRIVER=ODBC Driver 18 for SQL Server

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=whatsapp:+14155238886
TWILIO_STATUS_CALLBACK_URL=https://your-public-url/twilio-status

GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.5-flash # Optional, defaults to gemini-2.5-flash if not set

PORT=5000
FLASK_DEBUG=true
```

Notes:
- GEMINI_API_KEY is only needed for voice-note transcription.
- TWILIO_STATUS_CALLBACK_URL is optional but recommended for delivery tracking.

## 2) Database Setup

Run SQL scripts in this order:
1. database/schema.sql
2. database/seed_data.sql
3. database/stored_procedures.sql

You can run them manually in SQL Server tools, or use the helper script:

```bash
python scripts/run_mssql.py --env-file .env --yes
```

## 3) Start The App

```bash
python app.py
```

Expected local URL:
- http://localhost:5000

Quick health check:

```bash
curl http://localhost:5000/health
```

## 4) Connect Twilio To Local App

If running locally, expose port 5000:

```bash
ngrok http 5000
```

Then configure your Twilio WhatsApp webhook URL to:
- https://your-ngrok-url/webhook

Set status callback URL to:
- https://your-ngrok-url/twilio-status

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| GET | /health | Service health check |
| POST | /webhook | Incoming WhatsApp webhook from Twilio |
| POST | /twilio-status | Delivery status callback from Twilio |
| GET | /api/prices/ | List latest prices |
| GET | /api/prices/<symbol> | Get one instrument price |
| POST | /api/orders/ | Place BUY/SELL order |
| GET | /api/orders/<phone_number> | Fetch recent order history |
| GET | /api/portfolio/<phone_number> | Fetch portfolio holdings |

## How The System Works

### Request Flow

1. User sends a WhatsApp message.
2. Twilio calls POST /webhook.
3. App reads message text (or transcribes audio if voice note).
4. Message parser classifies intent (prices, portfolio, history, buy, sell, help).
5. Service layer queries or updates SQL Server.
6. App returns TwiML response.
7. Twilio delivers reply to user.

### Core Components

- app.py
    Registers Flask app, CORS, logging, and all route blueprints.

- routes/webhook.py
    Twilio webhook handler. Accepts inbound messages, handles optional voice-note transcription, and sends TwiML responses.

- routes/services.py
    Main business logic:
    - intent parsing
    - symbol/quantity extraction
    - SQL Server connection and queries
    - order placement and portfolio updates
    - response text formatting

- routes/prices.py, routes/orders.py, routes/portfolio.py
    JSON APIs for prices, orders, and holdings.

- routes/twilio_status.py
    Receives Twilio delivery callbacks for outbound messages.

- routes/speech_to_text.py
    Downloads Twilio audio media and sends it to OpenAI transcription API.

## Supported Intent Examples

- show prices
- price of ZANACO
- buy 100 ZSUG
- sell 50 ZCCM
- my portfolio
- my orders
- help

## Troubleshooting

- Database connection errors:
    - Verify MSSQL_* values in .env
    - Confirm SQL Server is reachable and ODBC Driver 18 is installed

- Twilio webhook not receiving traffic:
    - Confirm ngrok is running
    - Verify Twilio webhook points to /webhook

- Voice note not transcribed:
    - Confirm OPENAI_API_KEY is set
    - Confirm TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN are valid

## Run A Quick Local API Check

```bash
curl http://localhost:5000/api/prices/
curl http://localhost:5000/api/portfolio/+260977123456
curl "http://localhost:5000/api/orders/+260977123456?limit=5"
curl -X POST http://localhost:5000/api/orders/ \
    -H "Content-Type: application/json" \
    -d '{"phone_number":"+260977123456","symbol":"ZANACO","order_type":"BUY","quantity":10}'
```
