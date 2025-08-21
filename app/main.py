import streamlit as st
import pandas as pd
import datetime
from db_handler import create_db,add_transaction, get_transactions, delete_transaction
from categorizer import categorize_transaction, load_category_keywords, ensure_csv_exists
from analysis import (
    load_transactions_df,
    make_monthly_spend_figure,
    make_category_spend_figure,
    top_n_transactions,
    make_cashflow_trend,
    make_cumulative_net_savings,
    make_spending_heatmap,
    make_rolling_avg_spending,
    make_category_share_over_time
)

from budget import (
    ensure_budget_schema,
    upsert_budget,
    get_budgets,
    delete_budget as delete_budget_row,
    build_budget_report,
    generate_tips,
)


# Initialize database if not present
create_db()

#calling ensure schema
ensure_budget_schema()


st.set_page_config(page_title="Personal Finance Tracker", layout="wide")

# Make sure the CSV template exists (helps new teammates)
ensure_csv_exists()


@st.cache_data
def get_category_map():
    return load_category_keywords()


# Sidebar Navigation
st.sidebar.header("Settings")
if st.sidebar.button("Reload categories.csv"):
    get_category_map.clear()  # picks up CSV edits without restarting the app
    st.sidebar.success("Categories reloaded!")

st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Manage Transactions", "All Transactions", "Visualization & Analysis", "Budgets & Tips"]
)


# ---------------- Manage Transactions ----------------
if page == "Manage Transactions":
    st.title("Manage Transactions")

    with st.form("transaction_form"):
        date = st.date_input("Date", datetime.date.today())
        description = st.text_input("Description")

        mapping = get_category_map()
        suggested_category = categorize_transaction(description, mapping) if description.strip() else ""

        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        category = st.text_input("Category (optional)", value=suggested_category)

        t_type = st.radio("Type", ["Expense", "Income"])

        submitted = st.form_submit_button("Add Transaction")

        if submitted:
            try:
                add_transaction(
                    date.isoformat(),
                    description,
                    amount,
                    category,
                    t_type.lower()
                )
                st.success(f"{t_type} added!")
            except ValueError as e:
                st.error(str(e))


# ---------------- All Transactions ----------------
elif page == "All Transactions":
    st.title("All Transactions")

    df = get_transactions()

    if df.empty:
        st.info("No transactions yet.")
    else:
        # Display with delete option
        st.dataframe(df, use_container_width=True)

        # Let user pick transaction to delete
        delete_id = st.number_input("Enter Transaction ID to delete", min_value=1, step=1)
        if st.button("Delete Transaction"):
            delete_transaction(delete_id)
            st.success(f"Transaction {delete_id} deleted!")


# ---------------- Dashboard / Visualizations ----------------
elif page == "Visualization & Analysis":
    st.title("Dashboard & Insights")

    vis_type = st.radio("See Visualisation", ["Month-wise spendings",
                                              "Categories-wise spending", 
                                              "Top transactions",
                                              "Cashflow Trend",
                                              "Cumulative Net Savings",
                                              "Spending Heatmap",
                                              "Rolling Average Spending",
                                              "Category Share Over Time"])

    # cached loader so UI snappy
    @st.cache_data
    def _load_df():
        return load_transactions_df()

    df = _load_df()

    if df.empty:
        st.info("No transactions yet. Add a transaction to see charts.")
    else:
        # Date filter defaults
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()
        col1, col2 = st.columns(2)
        with col1:
            start = st.date_input("Start date", min_value=min_date, value=min_date)
        with col2:
            end = st.date_input("End date", min_value=min_date, value=max_date)

        # Category multi-select
        cats = ["All"] + sorted(df["category"].dropna().unique().tolist())
        selected = st.multiselect("Categories (multi-select)", options=cats, default=["All"])
        if "All" in selected or not selected:
            selected_cats = None
        else:
            selected_cats = selected

        if vis_type == "Month-wise spendings":
            fig_month = make_monthly_spend_figure(df, start_date=start, end_date=end, categories=selected_cats)
            st.plotly_chart(fig_month, use_container_width=True)

        elif vis_type == "Categories-wise spending":
            fig_cat = make_category_spend_figure(df, start_date=start, end_date=end)
            st.plotly_chart(fig_cat, use_container_width=True)

        elif vis_type == "Top transactions":
            st.subheader("Top transactions")
            top_df = top_n_transactions(df, n=5)
            st.dataframe(top_df, use_container_width=True)
        
        elif vis_type == "Cashflow Trend":
            st.plotly_chart(make_cashflow_trend(df), use_container_width=True)

        elif vis_type == "Cumulative Net Savings":
            st.plotly_chart(make_cumulative_net_savings(df), use_container_width=True)

        elif vis_type == "Spending Heatmap":
            st.plotly_chart(make_spending_heatmap(df), use_container_width=True)

        elif vis_type == "Rolling Average Spending":
            st.plotly_chart(make_rolling_avg_spending(df), use_container_width=True)

        elif vis_type == "Category Share Over Time":
            st.plotly_chart(make_category_share_over_time(df), use_container_width=True)



# ---------------- Budgets & Tips ----------------
elif page == "Budgets & Tips":
    st.title("Budgets & Tips")

    # Choose month (period)
    today = datetime.date.today()
    sel_date = st.date_input("Select month", value=today)
    period = f"{sel_date.year:04d}-{sel_date.month:02d}"

    # Load current transactions and current budgets
    df = load_transactions_df()
    budgets_df = get_budgets(period)

    with st.expander("Add / Update Budget", expanded=True):
        # Category choices: derived from CSV mapping; include a special 'Overall'
        mapping = get_category_map()
        # Show only expense categories by default; still allow Overall
        cat_options = sorted([c for c in mapping.keys() if c.lower() != "income"])
        cat_options = ["Overall"] + cat_options

        bcol1, bcol2 = st.columns([2, 1])
        with bcol1:
            b_category = st.selectbox("Category", options=cat_options, index=0)
        with bcol2:
            b_amount = st.number_input("Monthly Budget Amount", min_value=0.0, step=100.0, value=0.0)

        if st.button("Save Budget"):
            try:
                if b_amount <= 0:
                    st.error("Budget amount must be positive.")
                else:
                    upsert_budget(period, b_category, b_amount)
                    st.success(f"Saved budget for {b_category} in {period}.")
            except Exception as e:
                st.error(str(e))

    st.subheader(f"Budgets for {period}")
    if budgets_df.empty:
        st.info("No budgets set for this month yet.")
    else:
        st.dataframe(budgets_df, use_container_width=True)

        # Delete a budget row by ID
        dcol1, dcol2 = st.columns([1, 3])
        with dcol1:
            del_id = st.number_input("Delete Budget ID", min_value=0, step=1, value=0)
        with dcol2:
            if st.button("Delete Budget"):
                if del_id > 0:
                    delete_budget_row(int(del_id))
                    st.success(f"Deleted budget id {del_id}")
                else:
                    st.warning("Enter a valid ID to delete.")

    # ---- Budget vs Actual + Projections ----
    if df.empty or budgets_df.empty:
        st.info("Add some transactions and budgets to see analysis.")
    else:
        report = build_budget_report(period, df, budgets_df)
        st.subheader("Budget vs. Actual (with projection)")
        st.dataframe(
            report[[
                "category", "budget", "actual", "variance",
                "pct_used", "projected", "proj_vs_budget", "ahead_of_pace"
            ]].rename(columns={
                "pct_used": "pct_used (0-∞)",
                "proj_vs_budget": "projected - budget",
                "ahead_of_pace": "ahead_of_pace_vs_pro_rata"
            }),
            use_container_width=True
        )

        # Quick tiles
        total_budget = float(report.loc[report["category"] != "Overall", "budget"].sum() +
                             report.loc[report["category"] == "Overall", "budget"].sum() * 0)
        # If user sets Overall, don't double count. So compute both ways:
        total_budget = float(report[report["category"] != "Overall"]["budget"].sum() or
                             report[report["category"] == "Overall"]["budget"].sum())
        total_actual = float(report["actual"].sum()) if (report["category"] == "Overall").any() else \
                       float(df[(df["date"].dt.strftime("%Y-%m") == period) & (df["type"] == "expense")]["amount"].sum())

        t1, t2, t3 = st.columns(3)
        with t1:
            st.metric("Total Budget", f"{total_budget:,.0f}")
        with t2:
            st.metric("Total Actual (to date)", f"{total_actual:,.0f}")
        with t3:
            # rough projection
            start, end = pd.Timestamp(f"{period}-01"), pd.Timestamp(f"{period}-01") + pd.offsets.MonthEnd(1)
            dim = (end - start).days + 1
            today = pd.Timestamp.today()
            if start.month == today.month and start.year == today.year:
                day_ratio = today.day / dim
            elif start < today.replace(day=1):
                day_ratio = 1.0
            else:
                day_ratio = 1 / dim
            projected_total = total_actual / max(0.5, day_ratio)
            st.metric("Projected Month-End", f"{projected_total:,.0f}")

        # ---- Tips ----
        st.subheader("Tips")
        tips = generate_tips(report, period, df)
        if not tips:
            st.success("All good! No issues detected for this month")
        else:
            for t in tips:
                st.write("• " + t)
