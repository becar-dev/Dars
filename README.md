# PrintShop Micro-CRM Telegram Bot

A local-only Telegram bot for a small print shop / stationery business to log every customer interaction and get quick business stats.

## Features

- Inline-menu start dashboard with quick actions:
  - ➕ Add New Customer
  - 📊 Today's Statistics
  - 📅 Weekly Statistics
  - 📦 Service Report
- FSM flow for customer logging:
  1. Service type selection
  2. Customer status selection
  3. Numeric order amount input (0 allowed)
- SQLite (`crm.db`) persistence (auto-created locally)
- Ready-to-use reports:
  - Today's visitors, real orders, inquiries, revenue
  - Last 7 days summary + most requested service
  - Service report with requested count, actual orders, and revenue per service

---

## Project structure

```text
Dars/
├── app/
│   ├── config.py
│   ├── db/
│   │   └── database.py
│   ├── handlers/
│   │   └── bot.py
│   ├── keyboards/
│   │   └── inline.py
│   ├── states/
│   │   └── customer_flow.py
│   └── utils/
│       └── middlewares.py
├── .env.example
├── .gitignore
├── main.py
└── requirements.txt
```

---

## Database schema

Table: `customers_log`

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `date DATETIME DEFAULT CURRENT_TIMESTAMP`
- `service TEXT`
- `status TEXT`
- `amount INTEGER`

---

## Local run instructions (step-by-step)

### 1) Create and activate a virtual environment

**Linux/macOS**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure token

1. Copy `.env.example` to `.env`
2. Put your Telegram bot token into `BOT_TOKEN`

```bash
cp .env.example .env
```

Then edit `.env`:

```env
BOT_TOKEN=123456:YOUR_TELEGRAM_TOKEN
```

### 4) Run

```bash
python main.py
```

After setting a valid token, the bot starts immediately and creates `crm.db` automatically in the project root if it doesn't exist.

---

## Input validation behavior

When entering amount in step 3:

- ✅ only non-negative integer values are accepted (`0`, `150`, `2000`, ...)
- ❌ any non-numeric input is rejected with warning and re-prompt

---

## Notes

- This project is intentionally local-first and serverless.
- `crm.db` is excluded from git and remains on your PC.
