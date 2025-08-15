import streamlit as st
from db_handler import add_transaction, get_transactions
import datetime


st.title("💰 Personal Finance Tracker")

with st.form("transaction_form"):
    date = st.date_input("Date", datetime.date.today())
    description = st.text_input("Description")
    amount = st.number_input("Amount", min_value=0.0, step=0.01)
    category = st.text_input("Category (optional)")
    submitted = st.form_submit_button("Add Transaction")
    
    if submitted:
        add_transaction(date.isoformat(), description, amount, category if category else None)
        st.success("Transaction added!")

st.subheader("All Transactions")
st.dataframe(get_transactions())
