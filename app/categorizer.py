import os
import csv
import re
from typing import Dict, List

CSV_PATH = "data/categories.csv"

# Default set written if CSV not found (so teammates get a template automatically)
DEFAULT_CATEGORIES = {
    "Food": ["restaurant", "cafe", "coffee", "lunch", "dinner", "snack", "pizza", "burger"],
    "Transport": ["uber", "ola", "taxi", "cab", "bus", "train", "fuel", "petrol", "diesel", "metro", "toll"],
    "Groceries": ["grocery", "supermarket", "mart", "vegetable", "veg", "fruit", "milk", "dairy", "kirana", "bigbasket"],
    "Rent": ["rent", "lease", "apartment", "room", "pg", "hostel"],
    "Entertainment": ["movie", "cinema", "netflix", "spotify", "hotstar", "game", "concert", "theatre"],
    "Bills": ["electricity", "water", "internet", "broadband", "wifi", "phone", "mobile", "recharge", "gas", "dth", "bill"],
    "Shopping": ["shopping", "mall", "clothes", "electronics", "shoes", "amazon", "flipkart", "myntra"],
    "Health": ["pharmacy", "medical", "medicine", "doctor", "hospital", "clinic"],
    "Education": ["tuition", "course", "exam", "book", "coaching", "udemy", "coursera"],
    "Travel": ["flight", "airline", "hotel", "booking", "trip", "airbnb", "luggage", "tourism"],
    "Income": ["salary", "stipend", "refund", "interest", "bonus", "cashback", "credit"],
    "Other": []
}

def ensure_csv_exists(path: str = CSV_PATH) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.isfile(path):
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Keywords"])
            for cat, keys in DEFAULT_CATEGORIES.items():
                writer.writerow([cat, ", ".join(keys)])
    return path

def load_category_keywords(path: str = CSV_PATH) -> Dict[str, List[str]]:
    ensure_csv_exists(path)
    mapping: Dict[str, List[str]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = (row.get("Category") or "").strip()
            kw_field = (row.get("Keywords") or "")
            keywords = [k.strip().lower() for k in kw_field.split(",") if k.strip()]
            if cat:
                mapping[cat] = keywords
    # Guarantee "Other" exists
    mapping.setdefault("Other", [])
    return mapping

def categorize_transaction(description: str, mapping: Dict[str, List[str]] = None) -> str:
    if not description:
        return "Other"
    if mapping is None:
        mapping = load_category_keywords()
    desc_lower = description.lower()
    for category, keywords in mapping.items():
        for kw in keywords:
            if kw and re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                return category
    return "Other"
