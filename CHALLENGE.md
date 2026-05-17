# Innovation Hub — WhatsApp Trading Bot Challenge

## Overview

You have been given a working WhatsApp chatbot that lets users check prices,
place orders, and view their portfolio via a numbered menu.

**Your challenge: extend the bot to understand natural language.**

Right now users must type `1`, `2`, `3`, or exact commands like `BUY 100 ZANACO`.
Build a layer that lets users say things like:

> *"show me the price of ZANACO"*
> *"I want to buy 200 shares of ZSUG"*
> *"what does my portfolio look like?"*

---

## What you need to build

Extend `routes/webhook.py` (or add your own module) so the bot can parse
free-form WhatsApp messages and route them to the correct action.

### Actions to support

| Action | Example messages |
|---|---|
| View all prices | "show prices", "market today", "what's trading?" |
| View price of one instrument | "price of ZANACO", "how much is ZSUG?" |
| Place a buy order | "buy 100 ZANACO", "I want 200 shares of PUMA" |
| Place a sell order | "sell 50 ZCCM", "offload my BATA shares" |
| View portfolio | "my portfolio", "show my holdings", "what do I own?" |
| View order history | "my orders", "recent transactions" |

### Available instruments

| Symbol | Name |
|---|---|
| ZANACO | Zambia National Commercial Bank |
| ZCCM | ZCCM Investments Holdings |
| ZSUG | Zambia Sugar |
| PUMA | Puma Energy Zambia |
| NANGA | Nanga Farms |
| BATA | Bata Shoes |
| PRIMA | Prima Reinsurance |
| LAFARGE | Lafarge Zambia |

---


## Deliverables

1. Your updated code in `routes/webhook.py` (or a new module it calls)
2. `APPROACH.md` — one page explaining your approach and any limitations

---

## Getting started

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # fill in your credentials
python app.py
```

Database setup — run these three scripts against your SQL Server instance in order:

```
database/schema.sql
database/seed_data.sql
database/stored_procedures.sql
```

Expose to the internet for Twilio:

```bash
ngrok http 5000
# Paste the HTTPS URL into Twilio Console → WhatsApp Sandbox
# → "When a message comes in" → https://<id>.ngrok.io/webhook
```

Test the API directly without WhatsApp:

```bash
curl http://localhost:5000/api/prices/
curl http://localhost:5000/api/prices/ZANACO
curl http://localhost:5000/api/portfolio/+260971000001

curl -X POST http://localhost:5000/api/orders/ \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"+260971000001","symbol":"ZANACO","order_type":"BUY","quantity":100}'
```
