# app/budget.py
import sqlite3
import pandas as pd
from typing import List, Tuple
from datetime import date
import calendar

from db_handler import DB_PATH  # reuse same SQLite file

# ---------- Schema / CRUD ----------

def ensure_budget_schema():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT NOT NULL,                  -- 'YYYY-MM'
            category TEXT NOT NULL,                -- 'Food', 'Rent', 'Overall', etc.
            amount REAL NOT NULL CHECK (amount > 0),
            UNIQUE(period, category)
        )
    """)
    conn.commit()
    conn.close()

def upsert_budget(period: str, category: str, amount: float):
    if amount <= 0:
        raise ValueError("Budget amount must be positive.")
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # SQLite UPSERT
    cur.execute("""
        INSERT INTO budgets (period, category, amount)
        VALUES (?, ?, ?)
        ON CONFLICT(period, category) DO UPDATE SET amount=excluded.amount
    """, (period, category, float(amount)))
    conn.commit()
    conn.close()

def get_budgets(period: str) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT id, period, category, amount FROM budgets WHERE period = ? ORDER BY category",
        conn, params=(period,)
    )
    conn.close()
    return df

def delete_budget(budget_id: int):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM budgets WHERE id = ?", (int(budget_id),))
    conn.commit()
    conn.close()

# ---------- Reporting / Tips ----------

def _month_bounds(period: str) -> Tuple[pd.Timestamp, pd.Timestamp, int, int]:
    """period: 'YYYY-MM' -> (start, end, days_in_month, days_elapsed)"""
    year, mon = map(int, period.split("-"))
    start = pd.Timestamp(year=year, month=mon, day=1)
    dim = calendar.monthrange(year, mon)[1]
    end = pd.Timestamp(year=year, month=mon, day=dim)

    today = pd.Timestamp(date.today())
    if start.year == today.year and start.month == today.month:
        days_elapsed = today.day
    elif start < today.replace(day=1):
        days_elapsed = dim  # past month -> full
    else:
        days_elapsed = 1    # future month -> avoid div by zero / crazy projections
    return start, end, dim, days_elapsed

def build_budget_report(period: str, tx_df: pd.DataFrame, budgets_df: pd.DataFrame) -> pd.DataFrame:
    """Return per-category budget vs actual with projections."""
    if tx_df is None or tx_df.empty:
        tx_df = pd.DataFrame(columns=["date", "amount", "category", "type"])
    tx = tx_df.copy()
    tx.columns = [c.lower() for c in tx.columns]

    start, end, dim, days_elapsed = _month_bounds(period)
    day_ratio = max(1, days_elapsed) / dim  # 0<ratio<=1

    # Filter month window
    tx = tx[(tx["date"] >= start) & (tx["date"] <= end)]
    # Expenses only for budget tracking
    if "type" in tx.columns:
        tx = tx[tx["type"].str.lower() == "expense"]

    # Actuals by category
    actuals = (
        tx.groupby("category", as_index=False)["amount"]
          .sum()
          .rename(columns={"amount": "actual"})
    )

    # Join budgets and actuals
    base = budgets_df.rename(columns={"amount": "budget"}).copy()
    df = base.merge(actuals, on="category", how="left")
    df["actual"] = df["actual"].fillna(0.0)

    # Support an 'Overall' budget row if user sets it
    if (base["category"] == "Overall").any():
        total_actual = tx["amount"].sum()
        df.loc[df["category"] == "Overall", "actual"] = total_actual

    # Metrics
    df["variance"] = df["budget"] - df["actual"]
    df["pct_used"] = (df["actual"] / df["budget"]).clip(lower=0)  # 0..inf
    # Projection using pace so far
    df["projected"] = (df["actual"] / max(0.5, day_ratio)).fillna(0.0)  # clamp to avoid wild at start of month
    df["proj_vs_budget"] = df["projected"] - df["budget"]

    # Pro-rata tracking (how far ahead/behind vs time)
    df["pro_rata_budget_to_date"] = df["budget"] * day_ratio
    df["ahead_of_pace"] = df["actual"] - df["pro_rata_budget_to_date"]
    return df.sort_values(["category"]).reset_index(drop=True)

def generate_tips(report_df: pd.DataFrame, period: str, tx_df: pd.DataFrame) -> List[str]:
    """Simple rules to surface helpful, specific tips."""
    tips: List[str] = []
    if report_df is None or report_df.empty:
        return tips

    start, end, dim, days_elapsed = _month_bounds(period)
    day_ratio = max(1, days_elapsed) / dim

    # Overall totals
    tx = tx_df.copy()
    tx.columns = [c.lower() for c in tx.columns]
    tx = tx[(tx["date"] >= start) & (tx["date"] <= end)]
    total_exp = tx[tx["type"] == "expense"]["amount"].sum() if "type" in tx.columns else tx["amount"].sum()
    total_inc = tx[tx["type"] == "income"]["amount"].sum() if "type" in tx.columns else 0.0
    projected_total_exp = total_exp / max(0.5, day_ratio)

    # 1) Overshoot warnings per category (projection)
    overs = report_df[(report_df["budget"] > 0) & (report_df["projected"] > report_df["budget"] * 1.1)]
    for _, r in overs.iterrows():
        over_pct = (r["projected"] / r["budget"] - 1.0) * 100.0
        suggested_cut = min(20, max(5, round(over_pct)))  # 5–20% cut suggestion
        tips.append(
            f"*{r['category']}* is projected to exceed budget by ~{over_pct:.0f}%. "
            f"Try cutting this month’s spend by ~{suggested_cut}%."
        )

    # 2) Pace warnings (spent too fast vs time)
    pace = report_df[(report_df["budget"] > 0) & (report_df["ahead_of_pace"] > (0.15 * report_df["budget"]))]
    for _, r in pace.iterrows():
        pct_used = r["pct_used"] * 100
        tips.append(
            f"*{r['category']}*: {pct_used:.0f}% of budget used, "
            f"but only {day_ratio*100:.0f}% of the month passed. Slow down."
        )

    # 3) Net savings risk
    if total_inc > 0 and projected_total_exp > total_inc * 1.05:
        tips.append(
            f"Projected total expenses may exceed income for {period}. "
            f"Consider pausing non-essential *Shopping/Entertainment*."
        )

    # 4) Concentration risk
    cat_share = (tx[tx["type"] == "expense"]
                 .groupby("category", as_index=False)["amount"].sum()
                 .sort_values("amount", ascending=False))
    if not cat_share.empty:
        top = cat_share.iloc[0]
        if top["amount"] >= 0.35 * total_exp and total_exp > 0:
            tips.append(
                f"*{top['category']}* is {top['amount']/max(total_exp,1e-9):.0%} of your expenses. "
                f"Look for 1–2 quick savings here."
            )

    return tips
