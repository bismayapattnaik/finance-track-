import asyncio
import os
import parser as msg_parser
from bank_parser import is_bank_sms, parse_bank_sms

texts = [
    "Hyyy",
    "Hy",
    "A/c *9850 debited Rs. 1.00 on 28-06-26 to 7008859825@s. UPI:617902924082. Not you? SMS BLOCK to 9289592895, Dial 1930 for Cyber Fraud - Indian Bank"
]

for text in texts:
    print(f"--- {text[:20]} ---")
    if is_bank_sms(text):
        print("Detected as bank SMS")
        print("Parsed:", parse_bank_sms(text))
    else:
        print("Not bank SMS")
        print("Parsed:", msg_parser.parse(text))
