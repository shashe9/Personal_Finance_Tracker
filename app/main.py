import streamlit as st
from db_handler import add_transaction, get_transactions
from categorizer import categorize_transaction,load_category_keywords, ensure_csv_exists
import datetime
from analysis import (
    load_transactions_df,
    make_monthly_spend_figure,
    make_category_spend_figure,
    top_n_transactions,
)


st.set_page_config(page_title="Personal Finance Tracker", layout="wide")


# Make sure the CSV template exists (helps new teammates)
ensure_csv_exists()

@st.cache_data
def get_category_map():
    return load_category_keywords()

st.sidebar.header("Settings")
if st.sidebar.button("Reload categories.csv"):
    get_category_map.clear()  # picks up CSV edits without restarting the app
    st.sidebar.success("Categories reloaded!")

# Sidebar Navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Go to",
    ["Manage Transactions", "All Transactions", "Visualization & Analysis"]
)



if page == "Manage Transactions":
    #Title
    st.title("Manage Transactions")

    with st.form("transaction_form"):
        date = st.date_input("Date", datetime.date.today())
        description = st.text_input("Description")

        mapping = get_category_map()
        suggested_category = categorize_transaction(description, mapping) if description.strip() else ""

        amount = st.number_input("Amount", min_value=0.0, step=0.01)
        category = st.text_input("Category (optional)", value=suggested_category)

        submitted = st.form_submit_button("Add Transaction")
        
        if submitted:
            add_transaction(date.isoformat(), description, amount, category)
            st.success("Transaction added!")




elif page == "All Transactions":
    st.title("All Transactions")
    st.dataframe(get_transactions(), use_container_width=True)






# ---------------- Dashboard / Visualizations ----------------
elif page == "Visualization & Analysis":
    st.title("Dashboard & Insights")

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

        # Monthly spend figure
        fig_month = make_monthly_spend_figure(df, start_date=start, end_date=end, categories=selected_cats)
        st.plotly_chart(fig_month, use_container_width=True)

        # Category spend figure
        fig_cat = make_category_spend_figure(df, start_date=start, end_date=end)
        st.plotly_chart(fig_cat, use_container_width=True)

        # Top transactions
        st.subheader("Top transactions")
        top_df = top_n_transactions(df, n=5)
        st.dataframe(top_df, use_container_width=True)
