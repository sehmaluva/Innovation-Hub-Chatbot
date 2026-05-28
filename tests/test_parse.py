import sys
from unittest.mock import MagicMock

# Mock pyodbc before importing routes.services
sys.modules['pyodbc'] = MagicMock()

from routes.services import parse_message

phrases = [
    'show prices',
    'price of ZANACO',
    'buy 100 ZSUG',
    'sell 50 ZCCM',
    'my portfolio',
    'recent transactions',
    "what's trading?",
    'I want 200 shares of PUMA'
]

for phrase in phrases:
    result = parse_message(phrase)
    print(f"Phrase: {phrase} -> Intent: {result}")
