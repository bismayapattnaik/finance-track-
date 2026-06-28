"""
bot.py — Telegram bot for the personal expense tracker.

Commands:
  /start  — Welcome message
  /help   — Usage examples
  /total  — Month total vs budget
  /undo   — Delete last entry
  /budget — Per-category budget overview

Plain text messages are parsed as expenses (or bank SMS) and logged automatically.
"""

import json
import os
from datetime import date

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# Avoid shadowing the built-in `parser` module
import parser as msg_parser
from bank_parser import is_bank_sms, parse_bank_sms
from db import init_db, add, undo_last, month_total, month_rows
from export import export

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_DIR = os.path.dirname(os.path.abspath(__file__))
_CONFIG_PATH = os.path.join(_DIR, 'config.json')

with open(_CONFIG_PATH, encoding='utf-8') as _f:
    _config = json.load(_f)

TOKEN = _config['telegram_token']
CURRENCY = _config.get('currency', '₹')
MONTHLY_BUDGET = _config.get('monthlyBudget', 50000)
BUDGETS = _config.get('budgets', {})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def format_indian(amount: float) -> str:
    """
    Format a number in the Indian numbering system (12,34,567).
    """
    num = int(round(amount))
    s = str(abs(num))
    if len(s) <= 3:
        formatted = s
    else:
        last3 = s[-3:]
        rest = s[:-3]
        # Group the remaining digits in pairs from right to left
        groups = []
        while rest:
            groups.append(rest[-2:])
            rest = rest[:-2]
        groups.reverse()
        formatted = ','.join(groups) + ',' + last3

    return f'-{formatted}' if num < 0 else formatted


def _progress_bar(current: float, total: float, width: int = 15) -> str:
    """Return a text-based progress bar."""
    if total <= 0:
        return '░' * width
    ratio = min(current / total, 1.0)
    filled = int(ratio * width)
    return '█' * filled + '░' * (width - filled)


def _current_month() -> str:
    """Return the current month as 'YYYY-MM'."""
    return date.today().strftime('%Y-%m')


# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        '👋 *Welcome to Expense Tracker!*\n\n'
        'Just send me your expenses in plain English:\n'
        '• `ola 300`\n'
        '• `swiggy 450 biryani`\n'
        '• `₹1.5k myntra shirt`\n'
        '• Forward a bank SMS directly\n\n'
        'Type /help for all commands.',
        parse_mode='Markdown',
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        '📖 *How to use:*\n\n'
        '*Log expenses:*\n'
        '• `ola 300` → ₹300 in Travel\n'
        '• `swiggy 450 biryani` → ₹450 in Food\n'
        '• `1.5k myntra shirt` → ₹1,500 in Clothes\n'
        '• `rent 15000` → ₹15,000 in Rent\n'
        '• `2l sip` → ₹2,00,000 in Investments\n\n'
        '*Log income:*\n'
        '• `salary 75000`\n'
        '• `cashback 50`\n'
        '• `refund 299`\n\n'
        '*Bank SMS:*\n'
        'Forward any bank debit/credit SMS and it\'ll be parsed automatically.\n\n'
        '*Commands:*\n'
        '/total — Month total vs budget\n'
        '/budget — Per-category budget usage\n'
        '/undo — Delete last entry\n'
        '/help — This message',
        parse_mode='Markdown',
    )


async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /total command — show month total vs budget."""
    month = _current_month()
    spent = month_total(month)
    bar = _progress_bar(spent, MONTHLY_BUDGET)
    pct = (spent / MONTHLY_BUDGET * 100) if MONTHLY_BUDGET > 0 else 0

    emoji = '🟢' if pct < 70 else ('🟡' if pct < 90 else '🔴')

    await update.message.reply_text(
        f'📊 *{month} Summary*\n\n'
        f'{emoji} {CURRENCY}{format_indian(spent)} / {CURRENCY}{format_indian(MONTHLY_BUDGET)}\n'
        f'`{bar}` {pct:.0f}%\n\n'
        f'Remaining: {CURRENCY}{format_indian(max(MONTHLY_BUDGET - spent, 0))}',
        parse_mode='Markdown',
    )


async def undo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /undo command — delete most recent entry."""
    chat_id = update.effective_chat.id
    deleted = undo_last(chat_id)

    if deleted is None:
        await update.message.reply_text('Nothing to undo.')
        return

    export()
    await update.message.reply_text(
        f'🗑️ Removed: {CURRENCY}{format_indian(deleted["amount"])} → '
        f'{deleted["category"].title()} ({deleted["note"]})',
    )


async def budget_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /budget command — per-category caps and current spend."""
    month = _current_month()
    rows = month_rows(month)

    # Aggregate expenses by category
    cat_totals: dict[str, float] = {}
    for r in rows:
        if r['type'] == 'expense':
            cat_totals[r['category']] = cat_totals.get(r['category'], 0) + r['amount']

    lines = ['📋 *Category Budgets*\n']
    for cat, cap in sorted(BUDGETS.items()):
        spent = cat_totals.get(cat, 0)
        bar = _progress_bar(spent, cap, width=10)
        emoji = '🟢' if spent < cap * 0.7 else ('🟡' if spent < cap * 0.9 else '🔴')
        lines.append(
            f'{emoji} *{cat.title()}*: {CURRENCY}{format_indian(spent)} / '
            f'{CURRENCY}{format_indian(cap)} `{bar}`'
        )

    # Show unlisted categories
    for cat, total_val in sorted(cat_totals.items()):
        if cat not in BUDGETS:
            lines.append(f'⚪ *{cat.title()}*: {CURRENCY}{format_indian(total_val)} (no cap)')

    await update.message.reply_text('\n'.join(lines), parse_mode='Markdown')

async def dashboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /dashboard command — send cloud URL."""
    # Assuming they use PythonAnywhere for hosting
    url = "https://bismaya17.pythonanywhere.com/dashboard.html"
    await update.message.reply_text(
        f'📊 Here is your live, 24/7 Cloud Dashboard URL:\n{url}\n\n*(This works from anywhere, even when your laptop is completely turned off!)*',
        parse_mode='Markdown'
    )

async def ask_expert_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ask command — talk to AI financial expert."""
    question = ' '.join(context.args)
    if not question:
        await update.message.reply_text("🤔 What is your financial question? \nUsage: `/ask Should I buy a new phone this month?`", parse_mode='Markdown')
        return

    gemini_key = CFG.config.get('gemini_api_key', '')
    if not gemini_key or gemini_key == 'YOUR_GEMINI_API_KEY':
        await update.message.reply_text("🤖 **AI Expert is offline!**\nYou need to add your free Gemini API key to your `config.json` to use the financial expert feature.", parse_mode='Markdown')
        return

    await update.message.reply_text("🧠 *Analyzing your finances...*", parse_mode='Markdown')
    
    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        
        # Get financial context
        month = _current_month()
        rows = month_rows(month)
        spent = sum(r['amount'] for r in rows if r['type'] == 'expense')
        income = sum(r['amount'] for r in rows if r['type'] == 'income')
        budget = CFG.monthlyBudget
        
        prompt = f"""
You are a brilliant, highly analytical Financial Advisor bot. 
The user is asking you for financial advice. Here is their current financial context for this month:
- Total Budget: {budget}
- Total Spent: {spent}
- Total Income: {income}
- Remaining Budget: {budget - spent}

User's Question: "{question}"

Answer directly, professionally, and keep it under 3 paragraphs. Use emojis where appropriate.
"""
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        
        await update.message.reply_text(response.text, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error talking to AI: {e}")


# ---------------------------------------------------------------------------
# ntfy.sh background listener
# ---------------------------------------------------------------------------

async def process_automated_message(app, text: str):
    """Process a message received from ntfy."""
    today = date.today().isoformat()
    chat_id = 8373063599  # User's chat_id from Shortcut
    
    parsed = None
    if is_bank_sms(text):
        parsed = parse_bank_sms(text)
    if parsed is None:
        parsed = msg_parser.parse(text)
        
    if parsed is None:
        await app.bot.send_message(
            chat_id=chat_id,
            text='🤔 Automated SMS received but couldn\'t parse it:\n`' + text + '`',
            parse_mode='Markdown'
        )
        return
        
    add(today, parsed['category'], parsed['amount'],
        parsed['note'], parsed['type'], chat_id)
        
    export()
    
    month = _current_month()
    spent = month_total(month)
    icon = '💰' if parsed['type'] == 'income' else '✅'
    arrow = '←' if parsed['type'] == 'income' else '→'

    await app.bot.send_message(
        chat_id=chat_id,
        text=(f'{icon} {CURRENCY}{format_indian(parsed["amount"])} '
              f'{arrow} {parsed["category"].title()} ({parsed["note"]})\n'
              f'📅 Month: {CURRENCY}{format_indian(spent)} / '
              f'{CURRENCY}{format_indian(MONTHLY_BUDGET)}')
    )

async def listen_ntfy(app):
    import httpx
    import asyncio
    url = "https://ntfy.sh/bismaya_finance_tracker_987/json"
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url) as response:
                    async for line in response.aiter_lines():
                        if line:
                            data = json.loads(line)
                            if data.get('event') == 'message':
                                text = data.get('message')
                                await process_automated_message(app, text)
        except Exception as e:
            print("ntfy error:", e)
            await asyncio.sleep(5)




# ---------------------------------------------------------------------------
# Message handler
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle plain-text messages — parse and log transactions."""
    text = update.message.text
    chat_id = update.effective_chat.id
    today = date.today().isoformat()

    # 1. Try bank SMS parser first
    parsed = None
    if is_bank_sms(text):
        parsed = parse_bank_sms(text)

    # 2. Fall back to natural-language parser
    if parsed is None:
        parsed = msg_parser.parse(text)

    # 3. If nothing parsed, reply with a hint
    if parsed is None:
        await update.message.reply_text(
            '🤔 Couldn\'t parse that. Try something like:\n'
            '`ola 300` or `swiggy 450 biryani`',
            parse_mode='Markdown',
        )
        return

    # 4. Save to database
    add(today, parsed['category'], parsed['amount'],
        parsed['note'], parsed['type'], chat_id)

    # 5. Re-export data.js
    export()

    # 6. Reply with confirmation
    month = _current_month()
    spent = month_total(month)
    icon = '💰' if parsed['type'] == 'income' else '✅'
    arrow = '←' if parsed['type'] == 'income' else '→'

    await update.message.reply_text(
        f'{icon} {CURRENCY}{format_indian(parsed["amount"])} '
        f'{arrow} {parsed["category"].title()} ({parsed["note"]})\n'
        f'📅 Month: {CURRENCY}{format_indian(spent)} / '
        f'{CURRENCY}{format_indian(MONTHLY_BUDGET)}',
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Initialise DB and start polling."""
    init_db()
    
    async def post_init(app: Application):
        import asyncio
        asyncio.create_task(listen_ntfy(app))
        
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(CommandHandler('total', total))
    app.add_handler(CommandHandler('undo', undo))
    app.add_handler(CommandHandler('budget', budget_cmd))
    app.add_handler(CommandHandler('dashboard', dashboard_cmd))
    app.add_handler(CommandHandler('ask', ask_expert_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print('Bot is running... Press Ctrl+C to stop.')
    app.run_polling()


if __name__ == '__main__':
    main()
