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
    ensure_budget_schema, upsert_budget, get_budgets, delete_budget,
    build_budget_report, generate_tips
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



elif page == "Budgets & Tips":
    st.title("Budgets & Tips")

    # Period selector (YYYY-MM)
    today = datetime.date.today()
    this_period = f"{today.year}-{today.month:02d}"
    period = st.selectbox(
        "Budget Month",
        [this_period],  # keep simple; you can add past months list later
        index=0
    )

    # ----- Add/Update Budget -----
    st.subheader("Set / Update Budget")
    mapping = get_category_map()
    cat_options = sorted([c for c in mapping.keys() if c.lower() != "other"] + ["Overall"])
    c1, c2 = st.columns([2,1])
    with c1:
        b_cat = st.selectbox("Category", cat_options, index=0)
    with c2:
        b_amt = st.number_input("Amount (₹)", min_value=0.0, step=500.0, value=0.0)
    if st.button("Save Budget"):
        if b_amt <= 0:
            st.error("Amount must be positive.")
        else:
            upsert_budget(period, b_cat, b_amt)
            st.success(f"Saved budget for {b_cat}: ₹{int(b_amt)}")

    # ----- Current Budgets -----
    st.subheader("Current Budgets")
    budgets_df = get_budgets(period)
    if budgets_df.empty:
        st.info("No budgets set for this month yet.")
    else:
        st.dataframe(budgets_df.rename(columns={"amount":"Budget (₹)"}), use_container_width=True)
        del_id = st.number_input("Delete budget row by ID", min_value=0, step=1, value=0)
        if st.button("Delete Budget"):
            if del_id > 0 and (budgets_df["id"] == del_id).any():
                delete_budget(int(del_id))
                st.success(f"Deleted budget id {int(del_id)}")
            else:
                st.error("Enter a valid ID from the table above.")

    # ----- Report & Insights -----
    st.subheader("Budget vs Actual Report")
    df = load_transactions_df()
    report = build_budget_report(period, df, get_budgets(period))

    if report.empty:
        st.info("Add some budgets and expenses to see insights.")
    else:
        # Pretty display with progress columns (if your Streamlit supports column_config)
        try:
            st.dataframe(
                report,
                use_container_width=True,
                column_config={
                    "Budget": st.column_config.NumberColumn("Budget (₹)", format="₹%d"),
                    "Actual": st.column_config.NumberColumn("Actual (₹)", format="₹%d"),
                    "Δ (Actual-Budget)": st.column_config.NumberColumn("Δ (₹)", format="₹%d"),
                    "% Used": st.column_config.ProgressColumn("% Used", format="%.0f%%", min_value=0, max_value=200),
                    "Month Elapsed": st.column_config.ProgressColumn("Month Elapsed", format="%.0f%%", min_value=0, max_value=100),
                    "Pace Gap": st.column_config.NumberColumn("Pace Gap (pp)", format="%.0f"),
                    "Projected End": st.column_config.NumberColumn("Projected End (₹)", format="₹%d"),
                    "Proj Δ": st.column_config.NumberColumn("Proj Δ (₹)", format="₹%d"),
                }
            )
        except Exception:
            # Fallback if older Streamlit
            st.dataframe(report, use_container_width=True)

        st.subheader("Tips")
        tips = generate_tips(report, period, df)
        if tips:
            for t in tips:
                st.markdown(f"- {t}")
        else:
            st.info("No special tips — you’re on track 🎉")
