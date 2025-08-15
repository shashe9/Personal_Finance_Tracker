# app/analysis.py
import pandas as pd
import plotly.express as px
from db_handler import get_transactions

def load_transactions_df() -> pd.DataFrame:
    """
    Load transactions from DB (via your db_handler) and normalize columns.
    Returns an empty DataFrame if no rows exist.
    """
    df = get_transactions()  # expects a pandas DataFrame
    if df is None or df.empty:
        return pd.DataFrame(columns=["id", "date", "description", "amount", "category"])

    # normalize column names to lowercase to be resilient
    df.columns = [c.lower() for c in df.columns]

    # Ensure expected columns exist
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["date"] = pd.NaT

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)
    else:
        df["amount"] = 0.0

    if "category" not in df.columns:
        df["category"] = "Other"
    else:
        df["category"] = df["category"].fillna("Other")

    # Add year_month string for grouping (YYYY-MM)
    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    return df

def make_monthly_spend_figure(df: pd.DataFrame, start_date=None, end_date=None, categories=None):
    """
    Returns a Plotly bar chart of monthly spending.
    - df: preprocessed DataFrame from load_transactions_df()
    - start_date/end_date: strings or pd.Timestamp (inclusive)
    - categories: list of category names to filter
    """
    if df.empty:
        return px.bar(title="Monthly Spending (no data)")

    dff = df.copy()
    if start_date is not None:
        dff = dff[dff["date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        dff = dff[dff["date"] <= pd.to_datetime(end_date)]
    if categories:
        dff = dff[dff["category"].isin(categories)]

    monthly = dff.groupby("year_month", as_index=False)["amount"].sum().sort_values("year_month")
    # If empty after filtering:
    if monthly.empty:
        return px.bar(title="Monthly Spending (no matching data)")

    fig = px.bar(
        monthly,
        x="year_month",
        y="amount",
        title="Monthly Spending",
        labels={"year_month": "Month", "amount": "Total Spend"},
        text_auto=".2s"
    )
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=50, b=100))
    return fig

def make_category_spend_figure(df: pd.DataFrame, start_date=None, end_date=None):
    """
    Returns a Plotly pie chart (donut) of spending by category.
    """
    if df.empty:
        return px.pie(title="Spending by Category (no data)")

    dff = df.copy()
    if start_date is not None:
        dff = dff[dff["date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        dff = dff[dff["date"] <= pd.to_datetime(end_date)]

    cat = dff.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    if cat.empty:
        return px.pie(title="Spending by Category (no matching data)")

    fig = px.pie(
        cat,
        values="amount",
        names="category",
        title="Spending by Category",
        hole=0.35
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig

def top_n_transactions(df: pd.DataFrame, n=5) -> pd.DataFrame:
    """
    Returns top N transactions by amount (descending).
    """
    if df.empty:
        return df
    return df.sort_values("amount", ascending=False).head(n).loc[:, ["date", "description", "amount", "category"]]
