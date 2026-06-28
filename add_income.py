from db import init_db, add, all_rows
from export import export
from datetime import date

init_db()
rows = all_rows()
chat_id = rows[0]['chat_id'] if rows else 8373063599

# Add 20000 income
add(date.today().isoformat(), 'salary', 20000.0, 'Starting income', 'income', chat_id)
print("Income added.")

# Export to update data.js and dashboard_mobile.html
export()
print("Exported.")
