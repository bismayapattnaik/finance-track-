"""
test_parser.py — Tests for parser.py and bank_parser.py.

Run with: pytest test_parser.py -v
"""

import pytest
from parser import parse, _extract_amount, _detect_category, _is_income
from bank_parser import is_bank_sms, parse_bank_sms


# ═══════════════════════════════════════════════════════════════════════════
# Amount extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestAmountExtraction:
    """Test the amount parsing logic."""

    def test_plain_number(self):
        result = parse('500')
        assert result is not None
        assert result['amount'] == 500

    def test_number_with_commas(self):
        result = parse('1,250')
        assert result is not None
        assert result['amount'] == 1250

    def test_k_suffix(self):
        result = parse('1.5k')
        assert result is not None
        assert result['amount'] == 1500

    def test_2_5k_suffix(self):
        result = parse('2.5k')
        assert result is not None
        assert result['amount'] == 2500

    def test_l_suffix(self):
        result = parse('2l')
        assert result is not None
        assert result['amount'] == 200000

    def test_rs_prefix(self):
        result = parse('rs 500')
        assert result is not None
        assert result['amount'] == 500

    def test_rupee_symbol(self):
        result = parse('₹500')
        assert result is not None
        assert result['amount'] == 500

    def test_rs_suffix(self):
        result = parse('500rs')
        assert result is not None
        assert result['amount'] == 500

    def test_rs_dot_prefix(self):
        result = parse('rs.500')
        assert result is not None
        assert result['amount'] == 500

    def test_amount_in_sentence(self):
        result = parse('spent 300 on ola')
        assert result is not None
        assert result['amount'] == 300

    def test_large_comma_number(self):
        result = parse('rent 15,000')
        assert result is not None
        assert result['amount'] == 15000


# ═══════════════════════════════════════════════════════════════════════════
# Category detection
# ═══════════════════════════════════════════════════════════════════════════

class TestCategoryDetection:
    """Test keyword-based category matching."""

    def test_ola_is_travel(self):
        result = parse('ola 300')
        assert result['category'] == 'travel'

    def test_swiggy_is_food(self):
        result = parse('swiggy 450')
        assert result['category'] == 'food'

    def test_blinkit_is_groceries(self):
        result = parse('blinkit 800')
        assert result['category'] == 'groceries'

    def test_myntra_is_clothes(self):
        result = parse('myntra 1500 shirt')
        assert result['category'] == 'clothes'

    def test_netflix_is_luxuries(self):
        result = parse('netflix 199')
        assert result['category'] == 'luxuries'

    def test_sip_is_investments(self):
        result = parse('sip 5000')
        assert result['category'] == 'investments'

    def test_rent_is_rent(self):
        result = parse('rent 15000')
        assert result['category'] == 'rent'

    def test_electricity_is_bills(self):
        result = parse('electricity 1200')
        assert result['category'] == 'bills'

    def test_doctor_is_health(self):
        result = parse('doctor 500 consultation')
        assert result['category'] == 'health'

    def test_udemy_is_education(self):
        result = parse('udemy 449 course')
        assert result['category'] == 'education'

    def test_unknown_is_other(self):
        result = parse('random stuff 200')
        assert result['category'] == 'other'

    def test_multiword_amazon_prime(self):
        result = parse('amazon prime 299')
        assert result['category'] == 'luxuries'

    def test_multiword_mutual_fund(self):
        result = parse('mutual fund 10000')
        assert result['category'] == 'investments'


# ═══════════════════════════════════════════════════════════════════════════
# Income detection
# ═══════════════════════════════════════════════════════════════════════════

class TestIncomeDetection:
    """Test income vs expense classification."""

    def test_salary_is_income(self):
        result = parse('got salary 75000')
        assert result is not None
        assert result['type'] == 'income'

    def test_cashback_is_income(self):
        result = parse('cashback 50')
        assert result is not None
        assert result['type'] == 'income'

    def test_refund_is_income(self):
        result = parse('refund 299')
        assert result is not None
        assert result['type'] == 'income'

    def test_regular_expense(self):
        result = parse('chai 20')
        assert result is not None
        assert result['type'] == 'expense'

    def test_bonus_is_income(self):
        result = parse('bonus 10000')
        assert result is not None
        assert result['type'] == 'income'


# ═══════════════════════════════════════════════════════════════════════════
# Note extraction
# ═══════════════════════════════════════════════════════════════════════════

class TestNoteExtraction:
    """Test that notes are cleaned up properly."""

    def test_simple_note(self):
        result = parse('ola 300')
        assert result is not None
        assert 'ola' in result['note'].lower()

    def test_filler_words_stripped(self):
        result = parse('spent 500 on swiggy')
        assert result is not None
        # 'spent', 'on' should be stripped
        assert 'swiggy' in result['note'].lower()

    def test_amount_stripped_from_note(self):
        result = parse('myntra 1500 shirt')
        assert result is not None
        assert '1500' not in result['note']


# ═══════════════════════════════════════════════════════════════════════════
# Edge cases
# ═══════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_no_amount(self):
        result = parse('just random text without numbers')
        assert result is None

    def test_empty_string(self):
        result = parse('')
        assert result is None

    def test_none_input(self):
        result = parse(None)
        assert result is None

    def test_just_a_number(self):
        result = parse('500')
        assert result is not None
        assert result['amount'] == 500
        assert result['category'] == 'other'
        assert result['type'] == 'expense'

    def test_whitespace_only(self):
        result = parse('   ')
        assert result is None


# ═══════════════════════════════════════════════════════════════════════════
# Bank SMS parsing
# ═══════════════════════════════════════════════════════════════════════════

class TestBankSMS:
    """Test bank SMS detection and parsing."""

    def test_is_bank_sms_debit(self):
        sms = 'INR 1,250.00 debited from A/c XX4532 on 12-Mar-26. UPI Ref: 409876123456. Info: UPI/SWIGGY'
        assert is_bank_sms(sms) is True

    def test_is_bank_sms_plain_text(self):
        assert is_bank_sms('ola 300') is False

    def test_is_bank_sms_empty(self):
        assert is_bank_sms('') is False

    def test_parse_debit_upi(self):
        sms = 'INR 1,250.00 debited from A/c XX4532 on 12-Mar-26. UPI Ref: 409876123456. Info: UPI/SWIGGY'
        result = parse_bank_sms(sms)
        assert result is not None
        assert result['amount'] == 1250.00
        assert result['type'] == 'expense'
        assert result['category'] == 'food'  # SWIGGY → food

    def test_parse_debit_pos(self):
        sms = 'Rs. 500.00 debited from a/c XX9082 at POS. Avl Bal: Rs 15,000'
        result = parse_bank_sms(sms)
        assert result is not None
        assert result['amount'] == 500.00
        assert result['type'] == 'expense'

    def test_parse_credit_card(self):
        sms = 'Rs.420 spent on HDFC Credit Card ending 1234 at SWIGGY on 2026-06-28'
        result = parse_bank_sms(sms)
        assert result is not None
        assert result['amount'] == 420.00
        assert result['type'] == 'expense'

    def test_parse_debit_simple(self):
        sms = 'Your a/c XXX1234 debited by Rs.1,500.00 on 28-Jun'
        result = parse_bank_sms(sms)
        assert result is not None
        assert result['amount'] == 1500.00
        assert result['type'] == 'expense'

    def test_parse_credit_neft_salary(self):
        sms = 'INR 75,000.00 credited to your a/c XX5678. NEFT/salary'
        result = parse_bank_sms(sms)
        assert result is not None
        assert result['amount'] == 75000.00
        assert result['type'] == 'income'

    def test_parse_cashback_credit(self):
        sms = 'Cashback of Rs.50 credited to your a/c'
        result = parse_bank_sms(sms)
        assert result is not None
        assert result['amount'] == 50.00
        assert result['type'] == 'income'

    def test_parse_refund_credit(self):
        sms = 'Refund of INR 299.00 credited to A/c XX1234'
        result = parse_bank_sms(sms)
        assert result is not None
        assert result['amount'] == 299.00
        assert result['type'] == 'income'

    def test_parse_none_for_invalid(self):
        result = parse_bank_sms('hello world')
        assert result is None

    def test_parse_none_for_empty(self):
        result = parse_bank_sms('')
        assert result is None
