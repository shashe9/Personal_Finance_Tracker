# 💰 Personal Finance Tracker

A lightweight Streamlit app to track **expenses & income**, auto‑categorize transactions using **ML + rules**, and visualize insights (cashflow, category breakdowns, trends). Built with **Python, SQLite, Pandas, Plotly, scikit‑learn**.

---

## ✨ Features

* **Add transactions** with type (**Expense**/**Income**), date, description, amount, category (auto‑suggested)
* **Auto‑categorization**: ML prediction with confidence + fallback to keyword rules from `data/categories.csv`
* **Edit taxonomy** quickly by editing `categories.csv` (no code changes)
* **Delete transactions** from the “All Transactions” page
* **Visual dashboards**: monthly spend, category share, cashflow trend, cumulative savings, heatmap, rolling averages, and more
* **SQLite persistence** in `data/transactions.db` (created automatically)
* **One‑click reload** of category keywords from the sidebar

---

## 🧰 Tech Stack

* **UI**: Streamlit + Plotly
* **Data**: SQLite, Pandas
* **ML**: scikit‑learn (`TfidfVectorizer` + Logistic Regression)
* **Language**: Python 3.10+

---

## 📁 Project Structure

```
Personal_Finance_Tracker/
├─ app/
│  ├─ __init__.py
│  ├─ main.py                  # Streamlit app (navigation + pages)
│  ├─ analysis.py              # All Plotly chart builders & data helpers
│  ├─ budget.py                # (Reserved) Budget logic & tips
│  ├─ categorizer.py           # Rule-based + ML hybrid categorizer + CLI tester
│  ├─ db_handler.py            # SQLite create/add/delete/get helpers
│  ├─ train_model.py           # Train text model from categories.csv → models/model.pkl
│  └─ __pycache__/
├─ data/
│  ├─ categories.csv           # Category → keywords list (editable)
│  └─ transactions.db          # SQLite DB (auto-created)
├─ models/
│  └─ model.pkl                # Saved ML pipeline (auto-created by train_model.py)
├─ venv/                       # Your virtual env (not tracked)
├─ requirements.txt
├─ .gitignore
└─ README.md
```


---

## 🚀 Quickstart (60 seconds)

```bash
# 1) Create & activate a venv (recommended)
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) (One-time) Train the ML model from categories.csv
python app/train_model.py

# 4) Run the app
streamlit run app/main.py
```

Open the URL printed by Streamlit (typically [http://localhost:8501](http://localhost:8501)).

---

## 🗄️ Database

* File: `data/transactions.db`
* Auto‑created by `create_db()` on app start.
* Table: `transactions` with columns:

  * `id` (INTEGER, PK, autoincrement)
  * `date` (TEXT, ISO `YYYY-MM-DD`)
  * `description` (TEXT)
  * `amount` (REAL, **positive**; validation prevents ≤ 0)
  * `category` (TEXT)
  * `type` (TEXT, one of `income`, `expense`)

**Deleting rows**: Go to **All Transactions** → enter the ID → **Delete Transaction**.

**Schema changes** (e.g., adding `type` later): If you see errors like *“no column named type”*, the simplest fix in dev is to delete `data/transactions.db` and restart the app to recreate the table.

---

## 🧠 Category System

* Authoritative file: `data/categories.csv`
* Format:

  ```csv
  Category,Keywords
  Food,"restaurant, cafe, coffee, lunch, dinner, snack, pizza, burger"
  Transport,"uber, ola, taxi, cab, bus, train, fuel, petrol, diesel, metro, toll"
  ...
  ```
* Update keywords → Click **Reload categories.csv** in the app’s sidebar to hot‑reload without restarting.

---

## 🤖 ML Auto‑Categorization

We use a **hybrid** approach in `app/categorizer.py`:

1. **ML prediction** (scikit‑learn pipeline saved as `models/model.pkl`)
2. If **confidence < threshold** (default 10%), **fallback** to rule‑based keyword match from `categories.csv`
3. If no match, assign **`Other`**

### Train the model

```bash
python app/train_model.py
```

This reads `data/categories.csv`, builds a supervised dataset, trains a TF‑IDF + Logistic Regression classifier, and saves **`models/model.pkl`**.

> ⚠️ **Version consistency:** Train and serve with the **same scikit‑learn version** to avoid `InconsistentVersionWarning`. Pin in `requirements.txt`, e.g. `scikit-learn==1.7.1`. If versions differ, retrain.

### Test predictions in CLI (no Streamlit)

```bash
python app/categorizer.py
```

You’ll see an interactive prompt:

```
Word/Phrase Categorizer
Type 'exit' to quit.

Enter text: zomato order
Predicted: Food (Confidence: 92.3%)
```

### Use in the app

`app/main.py` calls `categorizer.categorize_transaction(...)` to prefill the Category field when adding a transaction. The user can override before saving.

---

## 📊 Dashboards (Visualization & Analysis)

In **Visualization & Analysis** you’ll find:

* **Month‑wise Spending** (bar)
* **Category‑wise Spending** (donut)
* **Top Transactions** (table)
* **Cashflow Trend** (income − expense over time)
* **Cumulative Net Savings**
* **Spending Heatmap** (calendar‑style aggregation)
* **Rolling Average Spending**
* **Category Share Over Time**

Each chart respects the **date range** and **category filters** at the top of the page.

---

## 🧭 App Navigation

* **Manage Transactions**: Add new transactions. Fields: Date, Description, Amount (> 0), Category (auto‑suggested), Type (Expense/Income).
* **All Transactions**: View full table and delete by ID.
* **Visualization & Analysis**: Select a visualization via radio buttons, adjust date/category filters.

---

## 📦 Requirements

Common entries for `requirements.txt` (yours may already include these):

```
streamlit
pandas
plotly
scikit-learn
joblib
numpy
```

> Add any others you installed. Pin exact versions for stability across teammates.

---

## 🧪 Development Tips

* **Hot reload categories** via the sidebar button
* **Caching**: We use `@st.cache_data` to keep the UI snappy; after mutating data, clear caches or re‑run
* **Validation**: Amounts must be **positive**; invalid inputs do **not** create rows
* **Git**: Don’t commit `venv/` or `data/*.db`. Commit `data/categories.csv` so your teammate gets the same taxonomy.

### Suggested `.gitignore`

```
# Python
venv/
__pycache__/
*.py[cod]
*.egg-info/

# OS
.DS_Store
Thumbs.db

# App data
.data/
data/*.db
models/*.pkl
.env*
.streamlit/
```

---

## 🧯 Troubleshooting

**Q: "no such table: transactions"**
A: The DB hasn’t been created yet. Start the app once (it runs `create_db()`), or delete `data/transactions.db` and restart.

**Q: "table transactions has no column named type"**
A: You’re using an old DB file. Delete `data/transactions.db` and restart to recreate with the new schema.

**Q: scikit‑learn `InconsistentVersionWarning`**
A: Train and use the model with the **exact same** scikit‑learn version. Pin it in `requirements.txt` and retrain.

**Q: Negative amounts added as 0**
A: Fixed. We raise `ValueError` and **do not** insert when amount ≤ 0.

---

## 🗺️ Roadmap

* Budgets per category & month (UI + alerts)
* Smart tips (e.g., “Reduce dining out by 20% to hit budget”)
* Inline row editing in the transactions table
* Import statements from CSV/Excel/Bank exports
* User profiles (multi‑user DB)

---

## 🤝 Contributing

* Branch: `feature/<name>` → PR to `main`
* Keep PRs focused and small
* Update this README when you add capabilities

---

## 📄 License

MIT — free to use, modify, and share.

---

**Made with ❤️ by Shashank Shekhar and Subham**
