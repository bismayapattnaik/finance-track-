# 💸 Personal Expense Tracker

A fully offline, privacy-focused monthly expense tracker.  
Log expenses via **Telegram** (plain text or forwarded bank SMS) → stored in local **SQLite** → visualised in an **HTML dashboard**.

---

## 🚀 5-Step Setup

### 1. Create your Telegram Bot

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the **bot token** (looks like `123456789:ABCdefGHI...`)

### 2. Configure

Open `config.json` and paste your bot token:

```json
{
  "telegram_token": "YOUR_BOT_TOKEN_HERE",
  "currency": "₹",
  "monthlyBudget": 50000,
  "budgets": { ... }
}
```

### 3. Install Dependencies

```bash
pip install python-telegram-bot
```

For running tests:

```bash
pip install pytest
```

### 4. Start the Bot

```bash
python bot.py
```

You should see `🤖 Bot is running…` — now message your bot on Telegram!

### 5. View Dashboard

Open `dashboard.html` in your browser. Data is synced every time you log a transaction.

---

## 💬 Example Messages

### Manual Logging

| Message | Amount | Category | Type |
|---------|--------|----------|------|
| `ola 300` | ₹300 | Travel | Expense |
| `swiggy 450 biryani` | ₹450 | Food | Expense |
| `₹1.5k myntra shirt` | ₹1,500 | Clothes | Expense |
| `rent 15000` | ₹15,000 | Rent | Expense |
| `2l sip` | ₹2,00,000 | Investments | Expense |
| `salary 75000` | ₹75,000 | Other | Income |
| `cashback 50` | ₹50 | Other | Income |

### Bank SMS (Forward directly)

The bot automatically parses real Indian bank SMS:

```
INR 1,250.00 debited from A/c XX4532 on 12-Mar-26. UPI Ref: 409876123456. Info: UPI/SWIGGY
→ ₹1,250 | Food | Expense

INR 75,000.00 credited to your a/c XX5678. NEFT/salary
→ ₹75,000 | Other | Income

Cashback of Rs.50 credited to your a/c
→ ₹50 | Other | Income
```

### Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | Usage examples |
| `/total` | Month total vs budget with progress bar |
| `/budget` | Per-category budget overview |
| `/undo` | Delete the last logged entry |

---

## 📱 iOS Shortcut Setup (Brief)

You can automate bank SMS logging with an iOS Shortcut:

1. Create a new **Automation** → "When I receive a message containing…"
2. Filter for bank SMS patterns (e.g., "debited", "credited", "INR", "Rs.")
3. Use the **Get Contents of URL** action to send the SMS text to your Telegram bot via the Bot API:
   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage?chat_id=<CHAT_ID>&text=<SMS_TEXT>
   ```
4. The bot will parse and log it automatically

> For a detailed step-by-step guide, see the iOS Shortcuts documentation.

---

## 🔍 How to Find Your Chat ID

1. Start your bot on Telegram (send `/start`)
2. Visit this URL in your browser (replace `YOUR_TOKEN`):
   ```
   https://api.telegram.org/botYOUR_TOKEN/getUpdates
   ```
3. Look for `"chat":{"id":123456789}` in the JSON response
4. That number is your `chat_id`

Alternatively, message **@userinfobot** on Telegram — it will reply with your chat ID.

---

## 🏷️ Category Customisation

Edit the `CATEGORY_KEYWORDS` dict in `parser.py` to add/remove keywords:

```python
CATEGORY_KEYWORDS = {
    'travel': ['ola', 'uber', 'metro', ...],
    'food': ['swiggy', 'zomato', 'chai', ...],
    # Add your own:
    'subscriptions': ['netflix', 'spotify', 'youtube', 'apple'],
}
```

Also update `config.json` budgets to match any new categories:

```json
{
  "budgets": {
    "subscriptions": 2000
  }
}
```

---

## 📁 Project Structure

```
expense-tracker/
├── bot.py              # Telegram bot — entry point
├── parser.py           # Natural language expense parser
├── bank_parser.py      # Indian bank SMS parser
├── db.py               # SQLite database layer
├── export.py           # Export DB → data.js for dashboard
├── config.json         # Bot token, currency, budgets
├── expenses.db         # SQLite database (auto-created)
├── data.js             # Dashboard data (auto-generated)
├── dashboard.html      # Visual dashboard (open in browser)
├── test_parser.py      # Parser tests (pytest)
├── test_db.py          # Database tests (pytest)
└── README.md           # This file
```

### Module Dependencies

```
bot.py
 ├── parser.py          (natural language parsing)
 ├── bank_parser.py     (bank SMS parsing)
 │    └── parser.py     (reuses CATEGORY_KEYWORDS)
 ├── db.py              (SQLite storage)
 └── export.py          (data.js generation)
      └── db.py         (reads all rows)
```

---

## 🧪 Running Tests

```bash
pytest test_parser.py test_db.py -v
```

---

## 🔒 Privacy

- All data stays **local** — SQLite on your machine
- No cloud sync, no analytics, no tracking
- The `data.js` export **never** includes your Telegram token
- Dashboard runs entirely offline in your browser
