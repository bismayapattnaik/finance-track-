"""
export.py — Read the database and config, then write data.js for the dashboard.

The generated data.js exposes two globals:
  - window.EXPENSE_DATA  — array of transaction objects
  - window.EXPENSE_CONFIG — currency, budgets (never includes sensitive tokens)
"""

import json
import os
from db import all_rows

_DIR = os.path.dirname(os.path.abspath(__file__))


def export():
    """
    Export all transaction data and safe config values to data.js.

    Reads config.json for currency / budget settings, strips the
    telegram_token, and writes the result alongside the HTML dashboard.
    """
    config_path = os.path.join(_DIR, 'config.json')
    with open(config_path, encoding='utf-8') as f:
        config = json.load(f)

    rows = all_rows()

    # Build the data array (only fields the dashboard needs)
    data = [
        {
            'id': r['id'],
            'date': r['date'],
            'category': r['category'],
            'amount': r['amount'],
            'note': r['note'],
            'type': r['type'],
        }
        for r in rows
    ]

    # Build safe config (NEVER include telegram_token)
    expense_config = {
        'currency': config.get('currency', '₹'),
        'monthlyBudget': config.get('monthlyBudget', 50000),
        'budgets': config.get('budgets', {}),
    }

    data_js_path = os.path.join(_DIR, 'data.js')
    data_js_content = f'window.EXPENSE_DATA = {json.dumps(data, ensure_ascii=False)};\nwindow.EXPENSE_CONFIG = {json.dumps(expense_config, ensure_ascii=False)};\n'
    
    with open(data_js_path, 'w', encoding='utf-8') as f:
        f.write(data_js_content)

    # Generate portable dashboard_mobile.html
    dash_path = os.path.join(_DIR, 'dashboard.html')
    mobile_path = os.path.join(_DIR, 'dashboard_mobile.html')
    
    if os.path.exists(dash_path):
        with open(dash_path, 'r', encoding='utf-8') as f:
            html = f.read()
        
        # Replace the external script include with inline script
        inline_script = f'<script>\n{data_js_content}\n</script>'
        html = html.replace('<script src="data.js"></script>', inline_script)
        
        with open(mobile_path, 'w', encoding='utf-8') as f:
            f.write(html)

    return data_js_path


if __name__ == '__main__':
    path = export()
    print(f'Exported to {path}')
