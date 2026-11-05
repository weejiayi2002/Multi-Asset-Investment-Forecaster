import streamlit as st  # Turns code into websites
import pandas as pd
import plotly.express as px  # Draw nice interactive line charts
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import numpy as np
import json

# 1. Page Styling and Configuration
st.set_page_config(
    page_title="Multi-Asset Portfolio Forecaster",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern card metrics and clean UI
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 16px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-label { font-size: 0.8rem; color: #6c757d; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 1.5rem; color: #212529; font-weight: 700; margin-top: 4px; }
    .impact-box {
        background-color: #1b382b;
        border-left: 5px solid #2ecc71;
        padding: 14px;
        border-radius: 8px;
        margin-top: 10px;
        color: #e8f8f5
    }
    </style>
""", unsafe_allow_html=True)

START_DATE = datetime.today()

# 2. Yahoo Finance Live Engine
# ---------------------------------------------------------
# 2. Yahoo Finance Live Engine (Airtight & Bulletproof)
# ---------------------------------------------------------
@st.cache_data
def fetch_stock_cagr(ticker: str, lookback_years: int = 5):
    """Fetches real historical prices and computes annualized CAGR cleanly."""
    try:
        # yf.Ticker().history is 100x more stable and avoids MultiIndex bugs completely
        stock = yf.Ticker(ticker)
        hist = stock.history(period=f"{lookback_years}y")

        if hist.empty or len(hist) < 20:
            return 0.08, "Data unavailable (Default 8.0%)"

        # hist["Close"] in history() is ALREADY split and dividend adjusted!
        prices = hist["Close"].dropna()
        if len(prices) < 20:
            return 0.08, "Insufficient data (Default 8.0%)"

        start_price = float(prices.iloc[0])
        end_price = float(prices.iloc[-1])

        if start_price <= 0 or np.isnan(start_price) or np.isnan(end_price):
            return 0.08, "Calculation error (Default 8.0%)"

        cagr = (end_price / start_price) ** (1.0 / lookback_years) - 1.0

        if np.isnan(cagr):
            return 0.08, "Default to 8.0%"

        return float(cagr), f"Historical CAGR: {cagr:.2%}"
    except Exception as e:
        return 0.08, f"Fetch error: {e}"


# 3. Session State (Stores custom ad-hoc cash injections)
if "injections" not in st.session_state:
    st.session_state.injections = []

# 4. Sidebar: Multi Stock Asset Builder
popular_tickers = ["SPY", "QQQ", "VOO", "VWRA.L", "CSPX.L", "VT", "SMH",
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AMD"]
if "ticker_pool" not in st.session_state:
    st.session_state.ticker_pool = popular_tickers

# Check the locker for saved data
saved_profile_data = st.session_state.get("loaded_profile", None)

# Extract saved tickers (if they exist)
saved_tickers = saved_profile_data.get("tickers", []) if saved_profile_data else []

# Use saved tickers as the default!
selected_tickers = st.sidebar.multiselect(
    "Select Stocks / ETFs to Invest In:",
    options=st.session_state.ticker_pool + [t for t in saved_tickers if t not in st.session_state.ticker_pool],
    default=saved_tickers,
    help="You can also type any custom ticker from Yahoo Finance!"
)

if not selected_tickers:
    st.warning("Please select atleast one stock/ETF to begin")
    st.stop()

lookback = st.sidebar.selectbox("Historical Lookback Window", [3, 5, 10], index=1)
# --- 🗓️ SMART LIVING CALENDAR ENGINE ---
# Check if a restored profile has a permanent original start date & deadline
saved_profile_data = st.session_state.get("loaded_profile", None)

if saved_profile_data and "target_end_date" in saved_profile_data:
    original_start = datetime.strptime(saved_profile_data["start_date"], "%Y-%m-%d")
    target_end = datetime.strptime(saved_profile_data["target_end_date"], "%Y-%m-%d")

    # Calculate months elapsed and months remaining to permanent deadline
    months_passed = (START_DATE.year - original_start.year) * 12 + (START_DATE.month - original_start.month)
    total_months = max(1, (target_end.year - START_DATE.year) * 12 + (target_end.month - START_DATE.month))
    horizon_years = round(total_months / 12.0, 1)

    st.sidebar.success(
        f"⏳ **Goal Active:** Started {original_start.strftime('%b %Y')}\n\n"
        f"• **{months_passed} Months Elapsed**\n\n"
        f"• **{horizon_years} Years Remaining** (Finish: {target_end.strftime('%b %Y')})"
    )
    # Let user override if they want to extend their life goal
    horizon_years = st.sidebar.slider("Adjust Remaining Horizon (Years)", 1.0, 30.0, float(horizon_years), 0.5)
    total_months = int(horizon_years * 12)
else:
    # Standard fresh setup for Day 1
    horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 10)
    total_months = int(horizon_years * 12)
    target_end = START_DATE + relativedelta(months=total_months)



st.sidebar.markdown("---")
st.sidebar.header("💵 Starting and Monthly Allocation")

# Collect individual stock allocations
asset_config = {}
total_initial_cash = 0
total_monthly_cash = 0

for ticker in selected_tickers:
    with st.sidebar.expander(f"📌 {ticker} Settings", expanded=True):
        raw_rate, msg = fetch_stock_cagr(ticker, lookback)
        st.caption(f"📈 {msg}")

        # 1. Smart Default Suggestion:
        # If historical is > 20%, suggest 18% as a realistic mean-reverted rate.
        # Otherwise, suggest the actual historical rate.
        suggested_forward_rate = min(raw_rate, 0.18) if raw_rate > 0.25 else raw_rate

        # 2. Per-Stock Forward Return Input:
        forward_cagr = st.number_input(
            f"Expected Future CAGR (%/yr)",
            min_value=1.0,
            max_value=100.0,
            value=float(round(suggested_forward_rate * 100, 2)),
            format="%.2f",
            step=0.5,
            key=f"cagr_{ticker}_{lookback}",
            help=f"Historic was {raw_rate * 100:.1f}%. Adjust what you expect {ticker} to do over your horizon."
        ) / 100.0

        # Smart Default Suggestion
        is_capped = raw_rate > 0.25
        suggested_forward_rate = 0.18 if is_capped else raw_rate

        # 💡 DYNAMIC EXPLANATION FOR THE USER
        if is_capped:
            st.caption(
                f"🧠 **Auto-Dampened to 18.0%**: {ticker}'s past 5Y growth ({raw_rate * 100:.2f}%) "
                f"was reduced to a realistic long-term ceiling. *You can freely edit this above!*"
            )
        else:
            st.caption(
                f"📊 **Pre-Filled with 5Y History ({raw_rate * 100:.2f}%)**: "
                f"Based on real Yahoo Finance data. *You can freely edit this above!*"
            )

            #  Look inside the locker for this specific stock's saved money
            saved_init = 0.0
            saved_month = 0.0
            if saved_profile_data and ticker in saved_profile_data.get("allocations", {}):
                saved_init = saved_profile_data["allocations"][ticker]["initial"]
                saved_month = saved_profile_data["allocations"][ticker]["monthly"]

            # Draw the boxes using the saved money!
            c1, c2 = st.columns(2)
            with c1:
                init_val = st.number_input(f"Initial $", min_value=0.0, value=float(saved_init), step=50.0,
                                           key=f"init_{ticker}")
            with c2:
                month_val = st.number_input(f"Monthly $", min_value=0.0, value=float(saved_month), step=25.0,
                                            key=f"month_{ticker}")

            # --- 🏷️ INSTITUTIONAL ASSET CLASSIFICATION (Mauboussin / Damodaran Framework) ---
            if raw_rate > 0.25:
                tier_badge = "🔥 Tier 3: Hyper-Growth Momentum (>25%)"
                tier_color = "#e63946"
                show_two_stage = True  # 👈 SHOW and TURN ON for hot stocks like NVDA
                auto_two_stage = True
            elif raw_rate > 0.14:
                tier_badge = "🚀 Tier 2: High-Growth Blue-Chip (14% - 25%)"
                tier_color = "#f4a261"
                show_two_stage = True  # 👈 SHOW, but keep OFF by default for GOOGL
                auto_two_stage = False
            else:
                tier_badge = "🛡️ Tier 1: Steady / Mature Compounder (≤14%)"
                tier_color = "#2a9d8f"
                show_two_stage = False  # 👈 HIDE completely for VWRA / SPY!
                auto_two_stage = False

            st.markdown(
                f"<div style='font-size: 0.82rem; font-weight: 700; color: {tier_color}; margin-top: 6px; margin-bottom: 8px;'>"
                f"{tier_badge}"
                f"</div>",
                unsafe_allow_html=True
            )

            # Only show Two-Stage controls if the stock actually needs it!
            if show_two_stage:
                use_two_stage = st.checkbox(
                    "⚡ Two-Stage Growth Model",
                    value=auto_two_stage,
                    key=f"twostage_{ticker}",
                    help="Models near-term momentum followed by long-term cooldown to a mature rate."
                )
            else:
                use_two_stage = False

            if use_two_stage:
                stage1_years = st.slider(
                    f"Stage 1 Momentum Duration (Years)",
                    min_value=1,
                    max_value=min(horizon_years, 7),
                    value=3,
                    key=f"s1_yrs_{ticker}_{lookback}"
                )

                # Smart Adaptive Defaults:
                default_s1 = float(round(raw_rate * 100 * 0.75, 2)) if raw_rate > 0.25 else float(
                    round(raw_rate * 100, 2))
                default_s2 = 15.00 if raw_rate > 0.25 else 10.00  # Conservative 15% for hot stocks, 10% for blue-chips

                stage1_rate = st.number_input(
                    f"Stage 1 Momentum CAGR (%/yr)",
                    min_value=1.0, max_value=60.0, value=default_s1, format="%.2f", step=0.5, key=f"s1_rate_{ticker}_{lookback}"
                ) / 100.0

                stage2_rate = st.number_input(
                    f"Stage 2 Mature CAGR (Years {stage1_years + 1} to {horizon_years})",
                    min_value=1.0, max_value=30.0, value=default_s2, format="%.2f", step=0.5, key=f"s2_rate_{ticker}_{lookback}",
                    help="The realistic long-term rate once the hyper-growth phase cools down."
                ) / 100.0

                st.caption(
                    f"🚀 **Phase 1:** {stage1_rate * 100:.1f}% for {stage1_years} yrs $\\rightarrow$ "
                    f"📉 **Phase 2:** Cooldown to {stage2_rate * 100:.1f}% thereafter."
                )
            else:
                stage1_years = horizon_years
                stage1_rate = forward_cagr
                stage2_rate = forward_cagr

            # Save stage settings into asset_config
            asset_config[ticker] = {
                "initial": init_val,
                "monthly": month_val,
                "stage1_months": stage1_years * 12,
                "stage1_monthly_r": stage1_rate / 12.0,
                "stage2_monthly_r": stage2_rate / 12.0,
                "monthly_r": stage1_rate / 12.0,
                "cagr": stage1_rate
            }

        total_initial_cash += init_val
        total_monthly_cash += month_val

st.sidebar.info(
    f"**Total Capital Today:** ${total_initial_cash:,.0f} SGD\n\n**Total Monthly Flow:** ${total_monthly_cash:,.0f} SGD/mo")

# --- 💾 BACKUP & RESTORE (LIVING TIMELINE SAFE) ---
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Backup & Restore")

# Calculate permanent target deadline date to save
target_deadline_str = (START_DATE + relativedelta(months=total_months)).strftime("%Y-%m-%d")

# a) Download personal portfolio (Saves your permanent start date & finish line)
user_export_data = json.dumps({
    "start_date": saved_profile_data.get("start_date", START_DATE.strftime("%Y-%m-%d")) if saved_profile_data else START_DATE.strftime("%Y-%m-%d"),
    "target_end_date": target_deadline_str,
    "tickers": selected_tickers,
    "allocations": {t: {"initial": asset_config[t]["initial"], "monthly": asset_config[t]["monthly"]} for t in selected_tickers},
    "injections": st.session_state.injections
}, indent=4)

st.sidebar.download_button(
    label="📥 Download & Save My Plan (.json)",
    data=user_export_data,
    file_name="my_wealth_plan.json",
    mime="application/json",
    help="Saves your exact portfolio and permanent deadline directly to your computer."
)

# b) Upload file when visiting in the future
uploaded_profile = st.sidebar.file_uploader("📤 Restore Saved Plan", type=["json"])
if uploaded_profile is not None:
    try:
        profile_data = json.load(uploaded_profile)
        st.session_state.loaded_profile = profile_data
        st.session_state.injections = profile_data.get("injections", [])
        st.sidebar.success("✅ Goal Restored! Timeline updated automatically.")
    except Exception:
        st.sidebar.error("Invalid portfolio file.")


# 5. AD-HOC CASH INJECTION SIMULATOR
# ---------------------------------------------------------
st.title("💼 Multi-Asset Portfolio Forecaster")
st.caption(
    f"Projecting cashflow across {len(selected_tickers)} assets over a **{horizon_years}-Year ({total_months} Months)** timeline.")

with st.expander("⚡ Simulate an Ad-Hoc Cash Injection", expanded=True):
    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        # Allows picking from your current portfolio OR typing a brand new ticker!
        stock_choice = st.selectbox(
            "Target Stock",
            options=selected_tickers + ["➕ Other Custom Ticker..."]
        )
        if stock_choice == "➕ Other Custom Ticker...":
            inj_ticker = st.text_input("Type Ticker Symbol:", value="MSFT").upper()
        else:
            inj_ticker = stock_choice

    # Automatically fetch rate if it's a new custom ticker
    if inj_ticker not in asset_config:
        custom_rate, _ = fetch_stock_cagr(inj_ticker, lookback)
        target_rate = custom_rate / 12.0
    else:
        target_rate = asset_config[inj_ticker]["monthly_r"]
    with col_b:
        inj_month = st.number_input("In Which Month?", min_value=1, max_value=total_months, value=1)
    with col_c:
        inj_amount = st.number_input("Injection Amount ($)", min_value=0.0, value=0.0, step=100.0)
    with col_d:
        inj_note = st.text_input("Reason / Note", value="")

    # Math: What is the isolated impact of this single injection?
    if inj_ticker not in asset_config:
        custom_cagr, _ = fetch_stock_cagr(inj_ticker, lookback)
        asset_config[inj_ticker] = {
            "cagr": custom_cagr,
            "monthly_r": custom_cagr / 12.0,
            "initial": 0.0,
            "monthly": 0.0
        }

    target_rate = asset_config[inj_ticker]["monthly_r"]
    remaining_months = total_months - inj_month
    compounded_impact = inj_amount * ((1 + target_rate) ** remaining_months)
    pure_profit = compounded_impact - inj_amount

    future_date = (START_DATE + relativedelta(months=inj_month)).strftime("%B %Y")

    st.markdown(f"""
        <div class="impact-box">
            <b>💡 Decision Impact:</b> Injecting <b>${inj_amount:,.0f} SGD</b> into <b>{inj_ticker}</b> on <b>{future_date} (Month {inj_month})</b> 
            leaves it to compound for <b>{remaining_months} months</b>.<br>
            By the end of Year {horizon_years}, that single injection alone grows into 
            <b style="color: #2e7d32;">${compounded_impact:,.0f} SGD</b> (+${pure_profit:,.0f} free profit)!
        </div>
    """, unsafe_allow_html=True)

    if st.button("➕ Lock This Injection Into Portfolio"):
        st.session_state.injections.append({
            "Ticker": inj_ticker,
            "Month": int(inj_month),
            "Amount": float(inj_amount),
            "Note": inj_note
        })
        st.success(f"Added ${inj_amount:,.0f} injection for {inj_ticker} at Month {inj_month}!")

# Display current active injections (with editing)
# ✅ NEW: SELECTIVE EDITING & TARGETED DELETION
if st.session_state.injections:
    with st.expander("📋 Manage Active Injections (Edit or Remove Selectively)", expanded=True):
        inj_df = pd.DataFrame(st.session_state.injections)

        # a) Editable Table (Click any cell to fix typos live!)
        edited_inj_df = st.data_editor(
            inj_df,
            num_rows="dynamic",
            use_container_width=True,
            key="inj_table_editor"
        )

        # Keep session state synced with your live edits
        st.session_state.injections = edited_inj_df.to_dict(orient="records")

        # b) Selective One-by-One Removal
        del_col1, del_col2 = st.columns([3, 1])

        with del_col1:
            # Build clear labels: e.g. "1: NVDA - $2,000 (Month 4: Internship Pay)"
            options_to_delete = [
                f"{i}: {row['Ticker']} - ${row['Amount']:,.0f} (Month {row['Month']}: {row.get('Note', '')})"
                for i, row in enumerate(st.session_state.injections)
            ]
            selected_to_delete = st.selectbox("Select specific injection to remove:", options=options_to_delete)

        with del_col2:
            st.write("")  # Spacer to align button
            st.write("")
            if st.button("❌ Remove"):
                idx_to_remove = int(selected_to_delete.split(":")[0])
                st.session_state.injections.pop(idx_to_remove)
                st.success("Removed!")
                st.rerun()

        # c) Emergency Clear All (With confirmation guard)
        st.markdown("---")
        if st.button("⚠️ Clear All Injections (Reset Table)"):
            st.session_state.injections = []
            st.rerun()

# ---------------------------------------------------------
# ---------------------------------------------------------
# 6. MULTI-ASSET RECURSIVE COMPOUNDING ENGINE
# ---------------------------------------------------------
dates_timeline = [START_DATE + relativedelta(months=i) for i in range(total_months + 1)]

# Pre-process injections into a quick lookup: {(ticker, month): total_amount}
injection_map = {}
for item in st.session_state.injections:
    key = (item["Ticker"], item["Month"])
    injection_map[key] = injection_map.get(key, 0.0) + item["Amount"]

# Make sure all tickers are tracked cleanly
all_active_tickers = list(asset_config.keys())

# Initialize starting points
asset_histories = {ticker: [asset_config[ticker]["initial"]] for ticker in all_active_tickers}
current_balances = {ticker: asset_config[ticker]["initial"] for ticker in all_active_tickers}
cost_basis_history = [total_initial_cash]
running_cost = total_initial_cash

# Compounding Month-by-Month Loop
for m in range(1, total_months + 1):
    month_total_deposit = 0.0

    for ticker in all_active_tickers:
        cfg = asset_config[ticker]

        # 🧠 Two-Stage Rate Selection
        if m <= cfg.get("stage1_months", total_months):
            r = cfg.get("stage1_monthly_r", cfg.get("monthly_r", 0.0))
        else:
            r = cfg.get("stage2_monthly_r", cfg.get("monthly_r", 0.0))

        # 1. Money makes money (compound interest)
        current_balances[ticker] *= (1 + r)

        # 2. Add regular monthly inflow
        current_balances[ticker] += cfg.get("monthly", 0.0)
        month_total_deposit += cfg.get("monthly", 0.0)

        # 3. Add ad-hoc injection if present
        if (ticker, m) in injection_map:
            extra = injection_map[(ticker, m)]
            current_balances[ticker] += extra
            month_total_deposit += extra

        # 4. Save history for this month (Correct Indentation!)
        asset_histories[ticker].append(current_balances[ticker])

    running_cost += month_total_deposit
    cost_basis_history.append(running_cost)

# Build total portfolio trajectory across all active tickers
portfolio_history = [
    sum(asset_histories[ticker][i] for ticker in all_active_tickers)
    for i in range(total_months + 1)
]

final_wealth = portfolio_history[-1]
final_invested = cost_basis_history[-1]
final_pnl = final_wealth - final_invested
final_roi = (final_pnl / final_invested) * 100 if final_invested > 0 else 0.0

# ---------------------------------------------------------
# 7. PERFORMANCE OVERVIEW & VISUALIZATIONS
# ---------------------------------------------------------
st.subheader("Performance & Unrealized PnL")
k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Out-of-Pocket Cash</div>
            <div class="metric-value">${final_invested:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
with k2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Projected Final Wealth</div>
            <div class="metric-value" style="color: #0d6efd;">${final_wealth:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
with k3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Unrealized PnL (Pure Profit)</div>
            <div class="metric-value" style="color: #198754;">+${final_pnl:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
with k4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Total Portfolio ROI</div>
            <div class="metric-value" style="color: #198754;">+{final_roi:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

tab1, tab2 = st.tabs(["📈 Portfolio & Individual Stock Curves", "🍰 Final Allocation Pie Chart"])

with tab1:
    fig = go.Figure()

    # Total Combined Portfolio
    fig.add_trace(go.Scatter(
        x=dates_timeline, y=portfolio_history,
        mode='lines', name='TOTAL PORTFOLIO',
        line=dict(color='#0d6efd', width=4)
    ))

    # Individual Stock Lines
    colors = px.colors.qualitative.Plotly
    for idx, ticker in enumerate(selected_tickers):
        fig.add_trace(go.Scatter(
            x=dates_timeline, y=asset_histories[ticker],
            mode='lines', name=f'{ticker} ({asset_config[ticker]["cagr"] * 100:.1f}%)',
            line=dict(width=2, color=colors[idx % len(colors)])
        ))

    # Total Cash Deposited (Cost Basis)
    fig.add_trace(go.Scatter(
        x=dates_timeline, y=cost_basis_history,
        mode='lines', name='Total Cash Deposited',
        line=dict(color='#adb5bd', width=2, dash='dash')
    ))

    fig.update_layout(
        title="Multi-Stock Trajectory (With Custom Ad-Hoc Injections)",
        xaxis_title="Date",
        yaxis_title="Balance (SGD)",
        hovermode="x unified",
        template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    final_breakdown = {ticker: asset_histories[ticker][-1] for ticker in selected_tickers}
    fig_pie = px.pie(
        names=list(final_breakdown.keys()),
        values=list(final_breakdown.values()),
        title=f"Expected Asset Distribution at End of Year {horizon_years}",
        hole=0.4
    )
    st.plotly_chart(fig_pie, use_container_width=True)

st.caption("ℹ️ *Note: Projections are modeled in SGD. Long-term USD/SGD currency fluctuations are assumed to be neutral over multi-year horizons, consistent with standard wealth forecasting models.*")
