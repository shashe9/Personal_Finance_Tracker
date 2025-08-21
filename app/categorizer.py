import os
import re
import csv
import joblib

# -------------------------
# CONFIG
# -------------------------
CSV_PATH = "data/categories.csv"
MODEL_PATH = os.path.join(os.path.dirname(__file__), "model.pkl")
CONFIDENCE_THRESHOLD = 0.10  # 10% cutoff

# -------------------------
# CSV CATEGORY LOADER
# -------------------------
def load_category_keywords(path: str = CSV_PATH):
    mapping = {}
    if not os.path.exists(path):
        raise FileNotFoundError(f"Category CSV not found: {path}")
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cat = (row.get("Category") or "").strip()
            kw_field = (row.get("Keywords") or "")
            keywords = [k.strip().lower() for k in kw_field.split(",") if k.strip()]
            if cat:
                mapping[cat] = keywords
    mapping.setdefault("Other", [])
    return mapping


# -------------------------
# ML MODEL LOADER
# -------------------------
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at {MODEL_PATH}. Please train using train_model.py first.")

model = joblib.load(MODEL_PATH)
categories = model.classes_

# -------------------------
# HYBRID PREDICTOR
# -------------------------
def predict_category(text, mapping):
    if not text:
        return "Other", 0.0

    # Step 1: ML prediction
    probabilities = model.predict_proba([text])[0]
    max_index = probabilities.argmax()
    best_category = categories[max_index]
    best_confidence = probabilities[max_index]

    if best_confidence >= CONFIDENCE_THRESHOLD:
        return best_category, best_confidence * 100

    # Step 2: Keyword Fallback
    desc_lower = text.lower()
    for category, keywords in mapping.items():
        for kw in keywords:
            if kw and re.search(r"\b" + re.escape(kw) + r"\b", desc_lower):
                return category, best_confidence * 100  # return with ML confidence for info

    # Step 3: Default to "Other"
    return "Other", best_confidence * 100


# -------------------------
# DASHBOARD-FRIENDLY WRAPPER
# -------------------------
def categorize_transaction(description, mapping=None):
    """Return only category string (for Streamlit/main.py use)."""
    if mapping is None:
        mapping = load_category_keywords()
    category, _ = predict_category(description, mapping)
    return category


# -------------------------
# CLI TESTING
# -------------------------
if __name__ == "__main__":
    print("Hybrid Word/Phrase Categorizer (ML + CSV Fallback)")
    print("Type 'exit' to quit.\n")

    mapping = load_category_keywords()

    while True:
        text = input("Enter a word/phrase (or type 'exit' to quit): ").strip()
        if text.lower() == "exit":
            print("Exiting...")
            break

        category, confidence = predict_category(text, mapping)
        print(f"Final Category: {category}  (ML Confidence: {confidence:.2f}%)\n")


# -------------------------
# ENSURE CSV EXISTS
# -------------------------
def ensure_csv_exists(path: str = CSV_PATH):
    """Create categories.csv with a header if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Category", "Keywords"])
        print(f"Created template categories.csv at {path}")

