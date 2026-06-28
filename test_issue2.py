import asyncio
import os
import parser as msg_parser
from bank_parser import is_bank_sms, parse_bank_sms
from db import init_db, add
from export import export
from datetime import date

init_db()

texts = [
    "A/c *9850 debited Rs. 1.00 on 28-06-26 to 7008859825@s. UPI:617902924082. Not you? SMS BLOCK to 9289592895, Dial 1930 for Cyber Fraud - Indian Bank"
]

for text in texts:
    parsed = parse_bank_sms(text)
    print("Parsed:", parsed)
    
    chat_id = 969871158
    today = date.today().isoformat()
    try:
        add(today, parsed['category'], parsed['amount'], parsed['note'], parsed['type'], chat_id)
        print("add() successful")
        export()
        print("export() successful")
    except Exception as e:
        print("EXCEPTION:", e)
