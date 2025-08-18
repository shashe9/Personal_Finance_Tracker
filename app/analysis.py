# app/analysis.py
import pandas as pd
import plotly.express as px
from db_handler import get_transactions


def load_transactions_df() -> pd.DataFrame:
    """
    Load transactions from DB and normalize.
    Ensures type column is used (expense/income).
    """
    df = get_transactions()
    if df is None or df.empty:
        return pd.DataFrame(columns=["id", "date", "description", "amount", "category", "type"])

    # normalize columns
    df.columns = [c.lower() for c in df.columns]

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

    if "type" not in df.columns:
        df["type"] = "expense"  # fallback

    # Flip sign for expenses, keep income positive
    df["signed_amount"] = df.apply(
        lambda r: -r["amount"] if r["type"].lower() == "expense" else r["amount"],
        axis=1
    )

    df["year_month"] = df["date"].dt.to_period("M").astype(str)
    return df


def make_monthly_spend_figure(df: pd.DataFrame, start_date=None, end_date=None, categories=None):
    """
    Returns a Plotly bar chart of monthly net amounts (income - expenses).
    """
    if df.empty:
        return px.bar(title="Monthly Net (no data)")

    dff = df.copy()
    if start_date is not None:
        dff = dff[dff["date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        dff = dff[dff["date"] <= pd.to_datetime(end_date)]
    if categories:
        dff = dff[dff["category"].isin(categories)]

    monthly = dff.groupby("year_month", as_index=False)["signed_amount"].sum().sort_values("year_month")
    if monthly.empty:
        return px.bar(title="Monthly Net (no matching data)")

    fig = px.bar(
        monthly,
        x="year_month",
        y="signed_amount",
        title="Monthly Net (Income - Expense)",
        labels={"year_month": "Month", "signed_amount": "Net Amount"},
        text_auto=".2s",
        color="signed_amount",  # positive = income, negative = expense
        color_continuous_scale="RdYlGn"
    )
    fig.update_layout(xaxis_tickangle=-45, margin=dict(t=50, b=100))
    return fig


def make_category_spend_figure(df: pd.DataFrame, start_date=None, end_date=None):
    """
    Returns a Plotly pie chart of EXPENSES by category only.
    """
    if df.empty:
        return px.pie(title="Expenses by Category (no data)")

    dff = df.copy()
    if start_date is not None:
        dff = dff[dff["date"] >= pd.to_datetime(start_date)]
    if end_date is not None:
        dff = dff[dff["date"] <= pd.to_datetime(end_date)]

    # Filter only expenses (positive values for chart)
    expenses = dff[dff["type"].str.lower() == "expense"].copy()
    expenses["amount"] = expenses["amount"].abs()

    cat = expenses.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
    if cat.empty:
        return px.pie(title="Expenses by Category (no matching data)")

    fig = px.pie(
        cat,
        values="amount",
        names="category",
        title="Expenses by Category",
        hole=0.35
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    return fig


def top_n_transactions(df: pd.DataFrame, n=5) -> pd.DataFrame:
    """
    Returns top N transactions (both income & expense, sorted by absolute amount).
    """
    if df.empty:
        return df
    return (
        df.sort_values("amount", ascending=False)
          .head(n)
          .loc[:, ["date", "description", "amount", "category", "type"]]
    )



#Changes in analysis



def make_cashflow_trend(df):
    df["month"] = df["date"].dt.to_period("M").astype(str)
    flow = df.groupby(["month", "type"])["amount"].sum().reset_index()
    return px.bar(flow, x="month", y="amount", color="type", barmode="group",
                  labels={"month": "Month", "amount": "Amount", "type": "Type"},
                  title="Income vs Expense by Month")


def make_cumulative_net_savings(df):
    df_sorted = df.sort_values("date").copy()
    df_sorted["signed_amount"] = df_sorted.apply(
        lambda r: r["amount"] if r["type"] == "income" else -r["amount"], axis=1
    )
    df_sorted["cumulative"] = df_sorted["signed_amount"].cumsum()
    return px.line(df_sorted, x="date", y="cumulative",
                   labels={"date": "Date", "cumulative": "Net Savings"},
                   title="Cumulative Net Savings Over Time")


def make_spending_heatmap(df):
    df["weekday"] = df["date"].dt.day_name()
    df["hour"] = df["date"].dt.hour
    weekday_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    df["weekday"] = pd.Categorical(df["weekday"], categories=weekday_order, ordered=True)

    heatmap_data = df.pivot_table(index="weekday", columns="hour", values="amount", aggfunc="sum").fillna(0)
    return px.imshow(
        heatmap_data.to_numpy(),
        x=heatmap_data.columns.astype(str),
        y=heatmap_data.index.astype(str),
        labels=dict(x="Hour", y="Weekday", color="Amount"),
        aspect="auto",
        color_continuous_scale="Reds",
        title="Spending Heatmap (Weekday vs Hour)"
    )


def make_rolling_avg_spending(df, window=7):
    df_sorted = df.sort_values("date")
    df_sorted["rolling"] = df_sorted["amount"].rolling(window).mean()
    return px.line(df_sorted, x="date", y="rolling",
                   title=f"{window}-Day Rolling Average Spending")


def make_category_share_over_time(df):
    df["month"] = df["date"].dt.to_period("M").astype(str)
    monthly_cat = df.groupby(["month", "category"])["amount"].sum().reset_index()
    return px.area(monthly_cat, x="month", y="amount", color="category",
                   title="Monthly Spending by Category")