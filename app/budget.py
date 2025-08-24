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

# ---------- Helpers ----------

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

# ---------- Reporting / Tips ----------

def build_budget_report(period: str, tx_df: pd.DataFrame, budgets_df: pd.DataFrame) -> pd.DataFrame:
    """
    Return per-category Budget vs Actual with:
      - Budget, Actual, Δ (Actual - Budget)
      - % Used, Month Elapsed %, Pace Gap
      - Projected End-of-Month & Proj Δ
      - Status & Suggested Action
    """
    if tx_df is None or tx_df.empty:
        tx_df = pd.DataFrame(columns=["date", "amount", "category", "type"])
    tx = tx_df.copy()
    tx.columns = [c.lower() for c in tx.columns]

    if "date" in tx.columns:
        tx["date"] = pd.to_datetime(tx["date"], errors="coerce")

    start, end, dim, days_elapsed = _month_bounds(period)
    day_ratio = max(1, days_elapsed) / dim  # 0<ratio<=1
    elapsed_pct = day_ratio * 100.0

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
    if base.empty:
        # Return an empty structure with expected columns
        return pd.DataFrame(columns=[
            "Category","Budget","Actual","Δ (Actual-Budget)","% Used","Month Elapsed",
            "Pace Gap","Projected End","Proj Δ","Status","Suggested Action"
        ])

    df = base.merge(actuals, on="category", how="left")
    df["actual"] = df["actual"].fillna(0.0)
    df["budget"] = df["budget"].fillna(0.0)

    # Support an 'Overall' budget row if user sets it
    if (base["category"] == "Overall").any():
        total_actual = tx["amount"].sum()
        df.loc[df["category"] == "Overall", "actual"] = total_actual

    # Metrics
    df["delta"] = df["actual"] - df["budget"]  # positive means over budget
    df["pct_used"] = (df["actual"] / df["budget"].replace(0, pd.NA)) * 100.0
    df["pct_used"] = df["pct_used"].fillna(0.0).clip(lower=0.0)

    # Projection using pace so far (clamped to avoid crazy early spikes)
    safe_ratio = max(0.5, day_ratio)
    df["projected_end"] = (df["actual"] / safe_ratio).fillna(0.0)
    df["proj_delta"] = df["projected_end"] - df["budget"]

    # Pace gap: how far % used is from elapsed %
    df["pace_gap"] = df["pct_used"] - elapsed_pct

    # Status & Action
    statuses = []
    actions  = []
    for _, r in df.iterrows():
        b = float(r["budget"])
        a = float(r["actual"])
        proj = float(r["projected_end"])
        d = float(r["delta"])
        proj_d = float(r["proj_delta"])
        used = float(r["pct_used"])

        if b == 0 and a == 0:
            statuses.append("— No budget set")
            actions.append("Set a realistic budget to start tracking.")
            continue
        if b == 0 and a > 0:
            statuses.append("❗ Spending without a budget")
            actions.append("Set a budget to control this category.")
            continue

        # Projected overshoot thresholds
        if proj_d > 0 and proj_d / b >= 0.10:
            statuses.append("❌ Over budget (projected)")
            cut_pct = min(20, max(5, round((proj_d / b) * 100)))
            actions.append(f"Cut spending by ~{cut_pct}%, postpone non-essentials.")
        elif d > 0:
            statuses.append("⚠️ Slightly over")
            cut_pct = min(10, max(5, round((d / b) * 100)))
            actions.append(f"Dial back by ~{cut_pct}% this month.")
        elif used > elapsed_pct + 10:
            statuses.append("⚠️ Ahead of pace")
            actions.append("Slow down for the rest of the month.")
        else:
            statuses.append("✅ On track")
            actions.append("Nice! Keep the same pace.")

    # Build display-friendly DataFrame
    out = pd.DataFrame({
        "Category": df["category"],
        "Budget": df["budget"].round(0),
        "Actual": df["actual"].round(0),
        "Δ (Actual-Budget)": df["delta"].round(0),
        "% Used": df["pct_used"].round(1),
        "Month Elapsed": round(elapsed_pct, 1),
        "Pace Gap": df["pace_gap"].round(1),
        "Projected End": df["projected_end"].round(0),
        "Proj Δ": df["proj_delta"].round(0),
        "Status": statuses,
        "Suggested Action": actions,
    }).sort_values("Category").reset_index(drop=True)

    return out

def generate_tips(report_df: pd.DataFrame, period: str, tx_df: pd.DataFrame) -> List[str]:
    """Simple, specific tips."""
    tips: List[str] = []
    if report_df is None or report_df.empty:
        return tips

    # 1) Pull 2–3 highest-risk rows by projected overshoot
    risky = report_df.copy()
    risky["risk"] = risky["Proj Δ"]
    risky = risky.sort_values("risk", ascending=False)
    risky = risky[risky["risk"] > 0].head(3)
    for _, r in risky.iterrows():
        b = r["Budget"]
        proj_over = r["Proj Δ"]
        over_pct = int(round((proj_over / b) * 100)) if b > 0 else 0
        tips.append(
            f"**{r['Category']}** projected +₹{int(proj_over)} (~{over_pct}%). "
            f"Action: {r['Suggested Action']}"
        )

    # 2) If many categories are “Ahead of pace”, add a general pacing tip
    ahead_count = (report_df["Status"] == "⚠️ Ahead of pace").sum()
    if ahead_count >= 2:
        tips.append("You’re ahead of pace in multiple categories. Consider a 1–2 week **spend freeze** on non-essentials.")

    # 3) If most categories are on track, celebrate + suggest saving
    on_track_ratio = (report_df["Status"] == "✅ On track").mean()
    if on_track_ratio >= 0.6:
        tips.append("Great job — most categories are **on track**. Consider moving surplus to savings/investments.")

    # De-duplicate
    tips = list(dict.fromkeys(tips))
    return tips
