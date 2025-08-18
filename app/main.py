import streamlit as st
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

# Initialize database if not present
create_db()

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
    ["Manage Transactions", "All Transactions", "Visualization & Analysis"]
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
