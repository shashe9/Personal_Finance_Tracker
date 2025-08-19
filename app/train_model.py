# app/train_model.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
import joblib
import os

# Path to CSV
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_PATH = os.path.join(BASE_DIR, "data", "categories.csv")

# Load dataset
df = pd.read_csv(CSV_PATH)

# Expand keywords into training samples
training_data = []
for _, row in df.iterrows():
    category = row["Category"]
    keywords = str(row["Keywords"]).split(",")
    for keyword in keywords:
        keyword = keyword.strip()
        if keyword:
            training_data.append((keyword, category))

train_df = pd.DataFrame(training_data, columns=["text", "category"])

# Build pipeline
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer()),
    ("clf", LogisticRegression(max_iter=1000))
])

# Train model
pipeline.fit(train_df["text"], train_df["category"])

# Save model
MODEL_PATH = os.path.join(BASE_DIR, "app", "model.pkl")
joblib.dump(pipeline, MODEL_PATH)

print(f"Model trained and saved at {MODEL_PATH}")
