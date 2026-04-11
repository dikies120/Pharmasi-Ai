"""Agent configuration constants"""

# Default thresholds for search parameters
DEFAULT_STOCK_THRESHOLD = 500
DEFAULT_PRICE_THRESHOLD = 50000

# Conversation context limits
CONVERSATION_HISTORY_LIMIT = 5
RECENT_CONTEXT_LIMIT = 10

# Valid operators for searches
VALID_OPERATORS = ["<", ">", "<=", ">=", "="]

# Keyword mappings for intent detection
KEYWORDS = {
    "stock": ["stok", "persediaan", "ketersediaan", "jumlah", "ada", "habis"],
    "price": ["harga", "mahal", "murah", "biaya", "tarif"],
    "expiry": ["kadaluarsa", "expired", "expire", "masa berlaku"],
    "info": ["fungsi", "indikasi", "dosis", "efek samping", "kandungan", "apa itu", "bagaimana cara"],
}

# Operator text to symbol mapping
OPERATOR_MAP = {
    "kurang dari sama dengan": "<=",
    "sampai": "<=",
    "mulai dari": ">=",
    "di bawah": "<",
    "kurang dari": "<",
    "lebih dari": ">",
    "di atas": ">",
    "habis": "=",
    "sama dengan": "=",
}

# Tool names
TOOLS = {
    "search_stock": "search_obat_by_stock",
    "search_price": "search_obat_by_harga",
    "search_expiry": "search_obat_by_kadaluarsa",
    "ask_question": "ask_question",
}
