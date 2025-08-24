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


# ---------------- Page Config ----------------
st.set_page_config(
    page_title="Personal Finance Tracker",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------- Ensure CSV / Data Exists ----------------
ensure_csv_exists()  # ensures templates exist for new users or teammates

# ---------------- Cached Data Load ----------------
@st.cache_data
def get_category_map():
    return load_category_keywords()

# ---------------- Sidebar: Header ----------------
st.sidebar.markdown("## ⚙️ Settings & Navigation")

# Reload categories CSV button
if st.sidebar.button("🔄 Reload Categories CSV"):
    get_category_map.clear()  # refresh cached categories
    st.sidebar.success("Categories reloaded successfully!")

st.sidebar.markdown("---")  # separator

# ---------------- Sidebar: Navigation ----------------
st.sidebar.markdown("### 📂 Go to")
page = st.sidebar.radio(
    label = "Navigate to",
    options=["Manage Transactions", "All Transactions", "Visualization & Analysis", "Budgets & Tips"],
    index=0
)

# Optional: Quick tips section in sidebar
with st.sidebar.expander("💡 Quick Tips", expanded=False):
    st.markdown("""
    - Use **Manage Transactions** to add or edit income/expense.
    - **All Transactions** shows a searchable & filterable transaction table.
    - Visualize trends and patterns under **Visualization & Analysis**.
    - Set monthly budgets and get smart tips in **Budgets & Tips**.
    - Reload categories CSV if you updated keywords without restarting.
    """)

# ---------------- Sidebar: Footer ----------------
st.sidebar.markdown("---")
st.sidebar.caption("Made with ❤️ using Streamlit\nPersonal Finance Tracker 2025")





# ---------------- Manage Transactions ----------------
if page == "Manage Transactions":
    st.markdown("## ✏️ Add / Manage Transactions")

    # Instruction container
    with st.expander("ℹ️ How to add a transaction", expanded=True):
        st.markdown(
            """
            - **Date**: When the transaction happened  
            - **Description**: What the transaction was for  
            - **Category**: Optional (auto-suggest based on description)  
            - **Amount**: Positive number  
            - **Type**: Expense or Income
            """
        )

    # Transaction form container
    with st.container():
        with st.form("transaction_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date_input = st.date_input("📅 Date", datetime.date.today())
                description_input = st.text_input("📝 Description")

            with col2:
                # Load category mapping (ensure latest)
                mapping = get_category_map()

                # Compute suggested category only if description is not empty
                suggested_category = categorize_transaction(description_input, mapping) if description_input.strip() else ""

                # Use session_state to preserve user edits
                if "category_input" not in st.session_state:
                    st.session_state.category_input = suggested_category

                # Update suggested category only if description changes
                if description_input.strip() and st.session_state.category_input != suggested_category:
                    st.session_state.category_input = suggested_category

                category_input = st.text_input(
                    "📂 Category (optional)",
                    value=st.session_state.category_input,
                    placeholder="Auto-suggested based on description"
                )

                # Update session state with user input
                st.session_state.category_input = category_input

                amount_input = st.number_input("💰 Amount", min_value=0.0, step=0.01)

            t_type = st.radio("Type", ["Expense", "Income"], horizontal=True)

            submitted = st.form_submit_button("➕ Add Transaction")

            if submitted:
                try:
                    if amount_input <= 0:
                        st.warning("⚠️ Amount must be greater than zero.")
                    else:
                        add_transaction(
                            date_input.isoformat(),
                            description_input,
                            amount_input,
                            category_input.strip() or "Other",
                            t_type.lower()
                        )
                        st.success(f"✅ {t_type} added successfully!")

                        # Clear inputs after successful submission
                        st.session_state.category_input = ""
                except ValueError as e:
                    st.error(f"❌ {str(e)}")

    # Optional: Show last 5 transactions as immediate feedback
    recent_tx = get_transactions().sort_values("date", ascending=False).head(5)
    if not recent_tx.empty:
        st.markdown("### 🕒 Recent Transactions")
        st.dataframe(
            recent_tx,
            use_container_width=True,
            height=300
        )


# ---------------- All Transactions ----------------
elif page == "All Transactions":
    st.title("💳 All Transactions")

    # Load and normalize
    df = get_transactions()
    if df is None or df.empty:
        st.info("No transactions yet.")
    else:
        # normalize column names to lowercase
        df.columns = [c.lower() for c in df.columns]

        # ensure optional columns exist
        if "category" not in df.columns:
            df["category"] = ""
        if "type" not in df.columns:
            df["type"] = ""

        # ensure date column is datetime
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # ---------- FILTERS ----------
        with st.expander("🔎 Filters", expanded=True):
            c1, c2, c3 = st.columns([1.5, 1.2, 1.2])

            # Date range
            min_date = df["date"].min().date() if not df["date"].isna().all() else datetime.date.today()
            max_date = df["date"].max().date() if not df["date"].isna().all() else datetime.date.today()
            with c1:
                start = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
                end = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)

            # Category filter
            cats = ["All"] + sorted(df["category"].dropna().unique().tolist())
            with c2:
                selected = st.multiselect("Category", options=cats, default=["All"])
                selected_cats = None if ("All" in selected or not selected) else selected

            # Type and search
            with c3:
                ttype = st.selectbox("Type", ["All", "Expense", "Income"], index=0)
                q = st.text_input("Search description (keywords)...")

            # Amount range
            a1, a2 = st.columns(2)
            with a1:
                min_amt = st.number_input("Min amount", value=0.0, step=10.0)
            with a2:
                max_amt = st.number_input("Max amount (0 = no limit)", value=0.0, step=10.0)

            # Sorting
            s1, s2 = st.columns([1, 1])
            with s1:
                sort_by = st.selectbox("Sort by", ["date", "amount", "category", "id"], index=0)
            with s2:
                sort_dir = st.selectbox("Order", ["Descending", "Ascending"], index=0)

        # ---------- APPLY FILTERS ----------
        dff = df.copy()
        dff = dff[(dff["date"] >= pd.to_datetime(start)) & (dff["date"] <= pd.to_datetime(end))]
        if selected_cats:
            dff = dff[dff["category"].isin(selected_cats)]
        if ttype != "All":
            dff = dff[dff["type"].str.lower() == ttype.lower()]
        if q and q.strip():
            dff = dff[dff["description"].fillna("").str.lower().str.contains(q.lower().strip())]
        if min_amt > 0:
            dff = dff[dff["amount"] >= float(min_amt)]
        if max_amt > 0:
            dff = dff[dff["amount"] <= float(max_amt)]
        ascending = sort_dir == "Ascending"
        if sort_by in dff.columns:
            dff = dff.sort_values(by=sort_by, ascending=ascending)
        else:
            dff = dff.sort_values(by="date", ascending=not ascending)

        # ---------- QUICK KPIs ----------
        exp_df = dff[dff["type"].str.lower() == "expense"]
        inc_df = dff[dff["type"].str.lower() == "income"]
        total_count = len(dff)
        total_spent = float(exp_df["amount"].sum()) if not exp_df.empty else 0.0
        total_income = float(inc_df["amount"].sum()) if not inc_df.empty else 0.0
        net = total_income - total_spent

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Transactions", f"{total_count}")
        k2.metric("Total Spent", f"₹{total_spent:,.2f}")
        k3.metric("Total Income", f"₹{total_income:,.2f}")
        k4.metric("Net (Income − Expense)", f"₹{net:,.2f}")

        # ---------- PAGINATION ----------
        page_size = st.selectbox("Rows per page", [5, 10, 20, 50], index=1)
        total_pages = max(1, (len(dff) + page_size - 1) // page_size)
        if "txn_page" not in st.session_state:
            st.session_state.txn_page = 1

        colp1, colp2, colp3 = st.columns([1, 2, 1])
        with colp1:
            if st.button("◀ Prev") and st.session_state.txn_page > 1:
                st.session_state.txn_page -= 1
        with colp2:
            st.write(f"Page {st.session_state.txn_page} of {total_pages}")
        with colp3:
            if st.button("Next ▶") and st.session_state.txn_page < total_pages:
                st.session_state.txn_page += 1

        page = st.session_state.txn_page
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        page_df = dff.iloc[start_idx:end_idx].copy()

        # ---------- DISPLAY TABLE ----------
        disp = page_df.loc[:, ["id", "date", "description", "category", "type", "amount"]].copy()
        disp["date"] = disp["date"].dt.strftime("%Y-%m-%d")
        disp["description"] = disp["description"].fillna("").apply(lambda s: s if len(s) <= 80 else s[:77] + "...")
        disp["amount"] = disp["amount"].apply(lambda x: f"₹{x:,.2f}")
        st.dataframe(disp.reset_index(drop=True), use_container_width=True, height=360)

        # ---------- DOWNLOAD FILTERED CSV ----------
        st.download_button(
            "⬇️ Download filtered CSV",
            data=dff.to_csv(index=False).encode("utf-8"),
            file_name=f"transactions_{start}_to_{end}.csv",
            mime="text/csv"
        )

        # ---------- DETAILS & DELETE ----------
        st.subheader("Transaction details / delete")
        ids = dff["id"].tolist()
        selected_id = st.selectbox("Select transaction ID", options=[0] + ids,
                                   format_func=lambda x: "— Select —" if x == 0 else str(x))
        if selected_id and selected_id != 0:
            tx_row = dff[dff["id"] == selected_id].iloc[0]
            st.markdown("**Full details:**")
            st.write(f"- **Date:** {pd.to_datetime(tx_row['date']).strftime('%Y-%m-%d')}")
            st.write(f"- **Description:** {tx_row['description']}")
            st.write(f"- **Category:** {tx_row.get('category', '—')}")
            st.write(f"- **Type:** {tx_row.get('type', '—')}")
            st.write(f"- **Amount:** ₹{tx_row['amount']:,.2f}")

            with st.form(key=f"del_form_{selected_id}"):
                st.write("If you want to delete this transaction, confirm below:")
                confirm = st.form_submit_button("🗑️ Delete transaction")
                if confirm:
                    delete_transaction(int(selected_id))
                    st.success(f"Transaction {selected_id} deleted.")
                    st.experimental_rerun()



# ---------------- Dashboard / Visualizations ----------------
elif page == "Visualization & Analysis":
    st.title("Dashboard & Insights")

    @st.cache_data
    def _load_df():
        return load_transactions_df()

    df = _load_df()

    if df.empty:
        st.info("No transactions yet. Add a transaction to see charts.")
    else:
        # ======= Filter Bar =======
        min_date = df["date"].min().date()
        max_date = df["date"].max().date()

        with st.container():
            st.markdown("##### Filters")
            c1, c2, c3 = st.columns([1.2, 1.2, 2])
            with c1:
                start = st.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
            with c2:
                end = st.date_input("End date", value=max_date, min_value=min_date, max_value=max_date)
            with c3:
                view = st.selectbox("Data View", ["Expenses", "Income", "Net"], index=0)

        # Category multi-select
        cats = ["All"] + sorted(df["category"].dropna().unique().tolist())
        selected = st.multiselect("Categories (multi-select)", options=cats, default=["All"])
        selected_cats = None if ("All" in selected or not selected) else selected

        # ======= Apply filters =======
        # Date range
        dff = df[(df["date"] >= pd.to_datetime(start)) & (df["date"] <= pd.to_datetime(end))].copy()
        # Categories
        if selected_cats:
            dff = dff[dff["category"].isin(selected_cats)]

        # Convenience views
        exp_df = dff[dff["type"].str.lower() == "expense"] if "type" in dff.columns else dff.copy()
        inc_df = dff[dff["type"].str.lower() == "income"] if "type" in dff.columns else dff.iloc[0:0].copy()

        # ======= KPI Cards =======
        total_spent = float(exp_df["amount"].sum())
        total_income = float(inc_df["amount"].sum())
        net = total_income - total_spent
        days = (pd.to_datetime(end) - pd.to_datetime(start)).days + 1
        daily_burn = (total_spent / days) if days > 0 else 0.0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Total Spent", f"₹{total_spent:,.0f}")
        k2.metric("Total Income", f"₹{total_income:,.0f}")
        k3.metric("Net (Income − Expense)", f"₹{net:,.0f}", delta=None)
        k4.metric("Avg Daily Spend", f"₹{daily_burn:,.0f}")

        st.caption(f"Showing data from **{start}** to **{end}**"
                   + ("" if not selected_cats else f" • Categories: {', '.join(selected_cats)}"))

        # ======= Tabs =======
        tab_overview, tab_trends, tab_table = st.tabs(["Overview", "Trends", "Table"])

        # ---------- OVERVIEW ----------
        with tab_overview:
            colA, colB = st.columns(2)

            if view == "Expenses":
                with colA:
                    st.subheader("Monthly Spending")
                    fig_month = make_monthly_spend_figure(exp_df, start_date=start, end_date=end, categories=selected_cats)
                    st.plotly_chart(fig_month, use_container_width=True)

                with colB:
                    st.subheader("Spending by Category")
                    if exp_df.empty:
                        st.info("No expense data in this range.")
                    else:
                        fig_cat = make_category_spend_figure(exp_df, start_date=start, end_date=end)
                        st.plotly_chart(fig_cat, use_container_width=True)

            elif view == "Income":
                with colA:
                    st.subheader("Monthly Income")
                    # reuse the same function but pass only income rows
                    fig_month = make_monthly_spend_figure(inc_df, start_date=start, end_date=end, categories=selected_cats)
                    st.plotly_chart(fig_month, use_container_width=True)

                with colB:
                    st.subheader("Income by Category")
                    if inc_df.empty:
                        st.info("No income data in this range.")
                    else:
                        fig_cat = make_category_spend_figure(inc_df, start_date=start, end_date=end)
                        st.plotly_chart(fig_cat, use_container_width=True)

            else:  # Net
                with colA:
                    st.subheader("Cashflow (Income vs Expense)")
                    st.plotly_chart(make_cashflow_trend(dff), use_container_width=True)
                with colB:
                    st.subheader("Cumulative Net Savings")
                    st.plotly_chart(make_cumulative_net_savings(dff), use_container_width=True)

            # Quick Insights
            with st.expander("🔎 Quick Insights", expanded=True):
                bullets = []
                if total_spent > 0:
                    cat_sum = exp_df.groupby("category", as_index=False)["amount"].sum().sort_values("amount", ascending=False)
                    if not cat_sum.empty:
                        top_cat = cat_sum.iloc[0]
                        share = (top_cat["amount"] / total_spent) * 100
                        bullets.append(f"**{top_cat['category']}** is your top expense category "
                                       f"(₹{top_cat['amount']:,.0f}, {share:.0f}% of spend).")
                if total_income == 0 and total_spent > 0:
                    bullets.append("No income recorded in this range; expenses are purely savings drawdown.")
                if net < 0:
                    bullets.append(f"You're **spending more than you earn** by ₹{abs(net):,.0f}. Consider trimming non-essentials.")
                if not bullets:
                    bullets.append("Looking good—nothing unusual to flag for this period.")
                for b in bullets:
                    st.markdown(f"- {b}")

        # ---------- TRENDS ----------
        with tab_trends:
            colT1, colT2 = st.columns(2)
            with colT1:
                st.subheader("Cashflow Trend")
                st.plotly_chart(make_cashflow_trend(dff), use_container_width=True)
            with colT2:
                st.subheader("Cumulative Net Savings")
                st.plotly_chart(make_cumulative_net_savings(dff), use_container_width=True)

            colT3, colT4 = st.columns(2)
            with colT3:
                st.subheader("Spending Heatmap")
                st.plotly_chart(make_spending_heatmap(dff), use_container_width=True)
            with colT4:
                st.subheader("30-Day Rolling Avg Spend")
                st.plotly_chart(make_rolling_avg_spending(dff), use_container_width=True)

            st.subheader("Category Share Over Time")
            st.plotly_chart(make_category_share_over_time(dff), use_container_width=True)

        # ---------- TABLE ----------
        with tab_table:
            st.subheader("Top Transactions")
            if view == "Income":
                base = inc_df
            else:
                base = exp_df if view == "Expenses" else dff
            top_df = top_n_transactions(base, n=10)
            st.dataframe(top_df, use_container_width=True)

            # Download filtered data
            st.download_button(
                "Download filtered dataset (CSV)",
                data=dff.to_csv(index=False).encode("utf-8"),
                file_name=f"transactions_{start}_to_{end}.csv",
                mime="text/csv",
                use_container_width=True,
            )


elif page == "Budgets & Tips":
    st.title("Budgets & Tips")

    # ---------------- Period Selector ----------------
    today = datetime.date.today()

    # last 6 months including current (so you can review/copy budgets)
    months = pd.period_range(
        end=pd.Timestamp(today.year, today.month, 1),
        periods=6, freq="M"
    ).astype(str).tolist()
    period = st.selectbox("Budget Month (YYYY-MM)", months, index=len(months)-1)

    # ---------------- Budget Setup ----------------
    st.header("Set / Update Budget")
    mapping = get_category_map()
    cat_options = sorted([c for c in mapping.keys() if c.lower() != "other"] + ["Overall"])

    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        b_cat = st.selectbox("Category", cat_options, index=0)
    with c2:
        b_amt = st.number_input("Amount (₹)", min_value=0.0, step=500.0, value=0.0)
    with c3:
        copy_prev = st.button("Copy last month's budgets")

    if st.button("Save Budget"):
        if b_amt <= 0:
            st.error("Amount must be positive.")
        else:
            upsert_budget(period, b_cat, b_amt)
            st.success(f"Saved budget for {b_cat}: ₹{int(b_amt)}")

    # Copy budgets from previous month (quick start)
    if copy_prev:
        # compute previous period
        yr, mo = map(int, period.split("-"))
        if mo == 1:
            prev_period = f"{yr-1}-12"
        else:
            prev_period = f"{yr}-{mo-1:02d}"

        prev_df = get_budgets(prev_period)
        if prev_df.empty:
            st.info(f"No budgets found for {prev_period}.")
        else:
            for _, r in prev_df.iterrows():
                upsert_budget(period, r["category"], float(r["amount"]))
            st.success(f"Copied {len(prev_df)} budget rows from {prev_period} → {period}")

    # ---------------- Current Budgets ----------------
    st.subheader("Current Budgets")
    budgets_df = get_budgets(period)
    if budgets_df.empty:
        st.info("No budgets set for this month yet.")
    else:
        # Show a clean table (hide id in the main table)
        st.dataframe(
            budgets_df.rename(columns={"amount": "Budget (₹)"}).drop(columns=["id"]),
            use_container_width=True
        )

        cdel1, cdel2 = st.columns([1, 1])
        with cdel1:
            del_id = st.number_input("Delete row by ID", min_value=0, step=1, value=0)
        with cdel2:
            if st.button("Delete Budget"):
                if del_id > 0 and (budgets_df["id"] == del_id).any():
                    delete_budget(int(del_id))
                    st.success(f"Deleted budget id {int(del_id)}")
                else:
                    st.error("Enter a valid ID from the current budgets table.")

    # ---------------- Budget Report & Insights ----------------
    st.header("Budget vs Actual")
    tx_df = load_transactions_df()
    report_raw = build_budget_report(period, tx_df, get_budgets(period))

    if report_raw.empty:
        st.info("Add some budgets and expenses to see insights.")
    else:
        # Normalize columns to consistent internal names
        R = report_raw.rename(columns={
            "Category": "category",
            "Budget": "budget",
            "Actual": "actual",
            "Δ (Actual-Budget)": "delta",
            "% Used": "used_pct",
            "Month Elapsed": "elapsed_pct",
            "Pace Gap": "pace_gap",
            "Projected End": "projected_end",
            "Proj Δ": "proj_delta",
            "Status": "status",
            "Suggested Action": "action",
        }).copy()

        # Totals (exclude 'Overall' to avoid double counting if user set it)
        R_no_overall = R[R["category"] != "Overall"]
        total_budget = float(R_no_overall["budget"].sum())
        total_actual = float(R_no_overall["actual"].sum())
        total_delta = total_actual - total_budget
        # Month elapsed is the same across rows; pick first non-null
        if "elapsed_pct" in R.columns and not R["elapsed_pct"].isna().all():
            month_elapsed = float(R["elapsed_pct"].dropna().iloc[0])
        else:
            month_elapsed = 0.0

        # -------- KPI cards --------
        st.subheader("Highlights")
        k1, k2, k3, k4 = st.columns(4)
        with k1:
            st.metric("Total Budget", f"₹{int(total_budget):,}")
        with k2:
            st.metric("Total Actual", f"₹{int(total_actual):,}",
                      delta=f"{(total_actual / total_budget * 100) if total_budget>0 else 0:.0f}% of budget")
        with k3:
            st.metric("Variance (Actual - Budget)", f"₹{int(total_delta):,}",
                      delta_color="inverse")
        with k4:
            st.metric("Month Elapsed", f"{month_elapsed:.0f}%", delta=None)

        # -------- Category cards grid (compact, readable) --------
        st.subheader("Per-Category Status")
        cat_rows = R[R["category"] != "Overall"].reset_index(drop=True)
        if not cat_rows.empty:
            cols_per_row = 3
            for i in range(0, len(cat_rows), cols_per_row):
                row_slice = cat_rows.iloc[i:i+cols_per_row]
                cols = st.columns(len(row_slice))
                for col, (_, r) in zip(cols, row_slice.iterrows()):
                    used_ratio = min(max((r["used_pct"] or 0) / 100.0, 0.0), 2.0)  # cap to 200%
                    badge = r.get("status", "—")
                    with col:
                        st.markdown(f"**{r['category']}**")
                        st.progress(min(used_ratio, 1.0), text=f"{r['used_pct']:.0f}% used")
                        c_a, c_b = st.columns(2)
                        with c_a:
                            st.caption(f"Budget: ₹{int(r['budget']):,}")
                            st.caption(f"Actual: ₹{int(r['actual']):,}")
                        with c_b:
                            st.caption(f"Projected: ₹{int(r['projected_end']):,}")
                            st.caption(f"Pace Gap: {r['pace_gap']:+.0f} pp")
                        # Status badge
                        if isinstance(badge, str) and "Over budget" in badge:
                            st.error(badge)
                        elif isinstance(badge, str) and "Ahead of pace" in badge:
                            st.warning(badge)
                        elif isinstance(badge, str) and "Slightly over" in badge:
                            st.warning(badge)
                        elif isinstance(badge, str) and "On track" in badge:
                            st.success(badge)
                        else:
                            st.info(badge)

        # -------- Core summary (narrow) --------
        st.subheader("Core Summary")
        core = R.loc[:, ["category", "budget", "actual", "delta", "used_pct"]].rename(columns={
            "category": "Category",
            "budget": "Budget (₹)",
            "actual": "Actual (₹)",
            "delta": "Δ (₹)",
            "used_pct": "% Used",
        })
        st.dataframe(core, use_container_width=True)

        # -------- Details (collapsed) --------
        with st.expander("Detailed Projections"):
            detail = R.loc[:, [
                "category", "projected_end", "proj_delta", "pace_gap", "elapsed_pct", "status", "action"
            ]].rename(columns={
                "category": "Category",
                "projected_end": "Projected End (₹)",
                "proj_delta": "Proj Δ (₹)",
                "pace_gap": "Pace Gap (pp)",
                "elapsed_pct": "Month Elapsed (%)",
                "status": "Status",
                "action": "Suggested Action"
            })
            st.dataframe(detail, use_container_width=True)

    # ---------------- Tips ----------------
    st.header("Personalized Tips")
    tips = generate_tips(report_raw, period, tx_df)
    if tips:
        for t in tips:
            tl = t.lower()
            if "exceed" in tl or "over budget" in tl or "overshoot" in tl:
                st.warning(t)
            elif "on track" in tl:
                st.success(t)
            else:
                st.info(t)
    else:
        st.success("No special tips — you’re on track!")
