"""
bank_parser.py — Parse real Indian bank SMS formats.

Supports HDFC, SBI, ICICI, Axis, Kotak and similar bank SMS patterns
for both debit and credit transactions.
"""

import re
from parser import CATEGORY_KEYWORDS

# ---------------------------------------------------------------------------
# Bank SMS detection
# ---------------------------------------------------------------------------

_BANK_INDICATORS = re.compile(
    r'(?:debited|credited|spent|withdrawn|deposited|a/c|acct|account|'
    r'upi\s*ref|imps|neft|rtgs|pos|atm|avl\s*bal|available\s*bal|'
    r'credit\s*card|debit\s*card)',
    re.IGNORECASE,
)

_AMOUNT_IN_SMS = re.compile(
    r'(?:inr|rs\.?)\s*[\d,]+(?:\.\d+)?',
    re.IGNORECASE,
)


def is_bank_sms(message: str) -> bool:
    """Return True if the message looks like an Indian bank SMS."""
    if not message:
        return False
    has_indicator = bool(_BANK_INDICATORS.search(message))
    has_amount = bool(_AMOUNT_IN_SMS.search(message))
    return has_indicator and has_amount


# ---------------------------------------------------------------------------
# Amount extraction from bank SMS
# ---------------------------------------------------------------------------

_SMS_AMOUNT = re.compile(
    r'(?:inr|rs\.?)\s*'
    r'(\d{1,3}(?:,\d{2,3})*(?:\.\d{1,2})?)',
    re.IGNORECASE,
)


def _extract_amount(message: str) -> float | None:
    """Extract the monetary amount from a bank SMS."""
    m = _SMS_AMOUNT.search(message)
    if m:
        return float(m.group(1).replace(',', ''))
    return None


# ---------------------------------------------------------------------------
# Transaction type detection
# ---------------------------------------------------------------------------

_DEBIT_KEYWORDS = re.compile(
    r'\b(?:debited|spent|withdrawn|purchased|paid|charged|deducted)\b',
    re.IGNORECASE,
)

_CREDIT_KEYWORDS = re.compile(
    r'\b(?:credited|received|deposited|refund|cashback|reversed)\b',
    re.IGNORECASE,
)


def _detect_type(message: str) -> str:
    """Return 'income' for credits, 'expense' for debits."""
    has_credit = bool(_CREDIT_KEYWORDS.search(message))
    has_debit = bool(_DEBIT_KEYWORDS.search(message))

    if has_credit and not has_debit:
        return 'income'
    if has_debit and not has_credit:
        return 'expense'
    # If both or neither, guess from position — credit keywords after amount
    # Default to expense
    if has_credit:
        return 'income'
    return 'expense'


# ---------------------------------------------------------------------------
# Merchant / info extraction
# ---------------------------------------------------------------------------

def _extract_merchant_info(message: str) -> str:
    """
    Try to extract merchant or transaction info from the SMS.
    Looks for patterns like:
      - Info: UPI/SWIGGY
      - at SWIGGY
      - at POS
      - NEFT/salary
      - Refund of ...
      - Cashback of ...
    """
    # Pattern: Info: ... (UPI reference info)
    m = re.search(r'info[:\s]+(.+?)(?:\.|$)', message, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Pattern: at MERCHANT on DATE
    m = re.search(r'\bat\s+([A-Za-z][\w\s&.]+?)(?:\s+on\b|\.|$)', message, re.IGNORECASE)
    if m:
        merchant = m.group(1).strip()
        # Filter out generic words
        if merchant.upper() not in ('POS', 'ATM'):
            return merchant

    # Pattern: to MERCHANT UPI: (Indian Bank format)
    m = re.search(r'\bto\s+([A-Za-z][\w\s&.]+?)\s+UPI:', message, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Pattern: linked to VPA (Indian Bank format)
    m = re.search(r'linked to VPA\s+([^;(\s]+(?:;[^(\s]+)?)', message, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Pattern: NEFT/something or UPI/something
    m = re.search(r'(?:NEFT|UPI|IMPS|RTGS)[/\\](\w+)', message, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # Pattern: Refund of / Cashback of
    m = re.search(r'(refund|cashback)\s+of\b', message, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    return ''


# ---------------------------------------------------------------------------
# Category detection (reuses CATEGORY_KEYWORDS from parser.py)
# ---------------------------------------------------------------------------

def _detect_category(text: str) -> str:
    """Match category from extracted merchant info or full SMS text."""
    lower = text.lower()
    # Multi-word keywords first
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if ' ' in kw and kw in lower:
                return cat
    # Single-word keywords
    words = set(re.findall(r'[a-z&]+', lower))
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if ' ' not in kw and kw in words:
                return cat
    return 'other'


# ---------------------------------------------------------------------------
# Note building
# ---------------------------------------------------------------------------

def _build_note(message: str, merchant: str) -> str:
    """Build a human-readable note from the SMS."""
    if merchant:
        return merchant
    # Fallback: strip amounts and common banking terms
    note = re.sub(
        r'(?:inr|rs\.?)\s*[\d,]+(?:\.\d+)?', '', message, flags=re.IGNORECASE,
    )
    note = re.sub(
        r'\b(?:debited|credited|from|to|your|a/c|acct|account|'
        r'xx\w+|on|ref|upi|neft|imps|rtgs|pos|atm|'
        r'avl\s*bal|available\s*balance)\b',
        '', note, flags=re.IGNORECASE,
    )
    note = re.sub(r'[:\s.]+', ' ', note).strip(' .,;-')
    return note if note else 'bank transaction'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_bank_sms(message: str) -> dict | None:
    """
    Parse an Indian bank SMS and extract transaction details.

    Returns dict with keys: amount, category, note, type
    Returns None if the message cannot be parsed.
    """
    if not message or not message.strip():
        return None

    amount = _extract_amount(message)
    if amount is None:
        return None

    txn_type = _detect_type(message)
    merchant = _extract_merchant_info(message)

    # Use merchant info + full message for category detection
    category_text = f'{merchant} {message}' if merchant else message
    category = _detect_category(category_text)

    note = _build_note(message, merchant)

    return {
        'amount': amount,
        'category': category,
        'note': note,
        'type': txn_type,
    }
