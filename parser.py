"""
parser.py — Turn a plain-English message into {amount, category, note, type}.

Handles Indian currency formats (rs, ₹, k, l suffixes) and detects
expense categories via keyword matching.
"""

import re

# ---------------------------------------------------------------------------
# Category keywords — edit these dicts to customise detection
# ---------------------------------------------------------------------------
CATEGORY_KEYWORDS = {
    'travel': [
        'ola', 'uber', 'metro', 'rapido', 'auto', 'cab', 'train',
        'flight', 'bus', 'petrol', 'diesel', 'parking',
    ],
    'food': [
        'swiggy', 'zomato', 'chai', 'restaurant', 'biryani', 'pizza',
        'burger', 'cafe', 'dominos', 'mcdonalds', 'kfc', 'dinner',
        'lunch', 'breakfast', 'snack',
    ],
    'groceries': [
        'blinkit', 'zepto', 'bigbasket', 'dmart', 'grocery',
        'vegetables', 'fruits', 'milk', 'supermarket',
    ],
    'clothes': [
        'myntra', 'ajio', 'shirt', 'jeans', 'shoes', 'zara',
        'h&m', 'dress', 'jacket', 'kurta',
    ],
    'rent': ['rent', 'pg', 'hostel', 'maintenance', 'society'],
    'bills': [
        'electricity', 'water', 'wifi', 'recharge', 'postpaid', 'gas',
        'internet', 'broadband', 'jio', 'airtel', 'vi',
    ],
    'luxuries': [
        'netflix', 'spotify', 'gym', 'movie', 'gaming',
        'amazon prime', 'hotstar', 'theatre', 'concert',
    ],
    'investments': [
        'sip', 'etf', 'stocks', 'mutual fund', 'fd', 'ppf', 'nps',
        'groww', 'zerodha', 'kuvera',
    ],
    'health': [
        'pharmacy', 'hospital', 'doctor', 'medicine', 'apollo',
        'medplus', 'lab', 'test', 'dental',
    ],
    'education': [
        'udemy', 'coursera', 'book', 'tuition', 'exam', 'college',
        'school', 'fees',
    ],
}

INCOME_KEYWORDS = [
    'salary', 'refund', 'cashback', 'received', 'credited',
    'bonus', 'reimbursement', 'interest', 'dividend',
]

# Words stripped from the note (filler / noise)
FILLER_WORDS = {
    'spent', 'on', 'for', 'at', 'rs', 'rs.', 'rupees', 'rupee',
    'inr', 'paid', 'bought', 'got', 'from', 'the', 'a', 'an',
    'my', 'to', 'in', 'of', 'with', 'via', 'through', 'just',
    'today', 'yesterday', 'some', 'about', 'around', 'approx',
}

# ---------------------------------------------------------------------------
# Amount extraction
# ---------------------------------------------------------------------------
# Matches patterns like: ₹500, rs 500, rs.500, 500rs, 1,250, 1.5k, 2l, 2.5k
_AMOUNT_PATTERN = re.compile(
    r'(?:₹|rs\.?\s*)'           # optional currency prefix (₹ or rs/rs.)
    r'(\d{1,3}(?:,\d{2,3})*'    # digits with optional commas
    r'(?:\.\d+)?)'               # optional decimal
    r'\s*([kl])?'                # optional k/l suffix
    r'|'                         # OR
    r'(\d{1,3}(?:,\d{2,3})*'    # digits with optional commas (no prefix)
    r'(?:\.\d+)?)'               # optional decimal
    r'\s*([kl])?'                # optional k/l suffix
    r'\s*(?:rs\.?|rupees?)?',    # optional currency suffix
    re.IGNORECASE,
)


def _extract_amount(message: str) -> float | None:
    """Return the first monetary amount found in *message*, or None."""
    # Try patterns with currency markers first, then bare numbers
    # Pattern 1: currency prefix  e.g. ₹500, rs 1.5k
    prefix_pat = re.compile(
        r'(?:₹|rs\.?\s*)'
        r'(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)'
        r'\s*([kl])?',
        re.IGNORECASE,
    )
    m = prefix_pat.search(message)
    if m:
        return _parse_number(m.group(1), m.group(2))

    # Pattern 2: number + currency suffix  e.g. 500rs, 1.5k rs
    suffix_pat = re.compile(
        r'(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)'
        r'\s*([kl])?\s*(?:rs\.?|rupees?)',
        re.IGNORECASE,
    )
    m = suffix_pat.search(message)
    if m:
        return _parse_number(m.group(1), m.group(2))

    # Pattern 3: bare number with optional k/l suffix
    bare_pat = re.compile(
        r'(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)'
        r'\s*([kl])\b',
        re.IGNORECASE,
    )
    m = bare_pat.search(message)
    if m:
        return _parse_number(m.group(1), m.group(2))

    # Pattern 4: plain number (at least 1 digit)
    plain_pat = re.compile(
        r'(?<!\w)(\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)(?!\w*[a-df-jm-zA-DF-JM-Z])',
    )
    m = plain_pat.search(message)
    if m:
        return _parse_number(m.group(1), None)

    return None


def _parse_number(raw: str, suffix: str | None) -> float:
    """Convert a raw digit string + optional k/l suffix to a float."""
    num = float(raw.replace(',', ''))
    if suffix:
        s = suffix.lower()
        if s == 'k':
            num *= 1_000
        elif s == 'l':
            num *= 100_000
    return num


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

def _detect_category(message: str) -> str:
    """Return the best-matching category or 'other'."""
    lower = message.lower()
    # Check multi-word keywords first (e.g. "amazon prime", "mutual fund")
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
# Income detection
# ---------------------------------------------------------------------------

def _is_income(message: str) -> bool:
    """Return True if the message describes income rather than an expense."""
    lower = message.lower()
    words = set(re.findall(r'[a-z]+', lower))
    return bool(words & set(INCOME_KEYWORDS))


# ---------------------------------------------------------------------------
# Note extraction
# ---------------------------------------------------------------------------

# Tokens that look like amount expressions (to strip from the note)
_AMOUNT_TOKEN = re.compile(
    r'(?:₹|rs\.?\s*)?'
    r'\d{1,3}(?:,\d{2,3})*(?:\.\d+)?'
    r'\s*(?:[kl])?\s*(?:rs\.?|rupees?)?',
    re.IGNORECASE,
)


def _extract_note(message: str) -> str:
    """Build a clean note from the original message."""
    # Remove amount tokens
    text = _AMOUNT_TOKEN.sub('', message)
    # Remove filler words and extra whitespace
    tokens = text.split()
    cleaned = [t for t in tokens if t.lower().strip('.,!?') not in FILLER_WORDS]
    note = ' '.join(cleaned).strip(' .,!?-–—')
    return note if note else 'expense'


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse(message: str) -> dict | None:
    """
    Parse a plain-English expense/income message.

    Returns dict with keys: amount, category, note, type
    Returns None if no amount is found.
    """
    if not message or not message.strip():
        return None

    amount = _extract_amount(message)
    if amount is None:
        return None

    category = _detect_category(message)
    txn_type = 'income' if _is_income(message) else 'expense'
    note = _extract_note(message)

    return {
        'amount': amount,
        'category': category,
        'note': note,
        'type': txn_type,
    }
