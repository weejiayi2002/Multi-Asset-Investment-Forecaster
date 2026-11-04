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
    page_title="Multi-Asset Portfolio Engine",
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
@st.cache_data(ttl=8640)
def fetch_stock_cagr(ticker: str, lookback_years: int = 5):
    """Fetches real historical prices and computes annualized CAGR without NaNs"""
    try:
        data = yf.download(ticker, period=f"{lookback_years}y", progress=False)
        if data.empty or len(data) < 20:
            return 0.08, "Data unvailable (Default 8.0%)"

        close_prices = data["Close"]
        if isinstance(close_prices, pd.DataFrame):
            close_prices = close_prices.iloc[:, 0]

        clean_prices = close_prices.dropna()
        if len(clean_prices) < 20:
            return 0.08, "Insufficient data (Default 8.0%)"

        start_price = float(close_prices.iloc[0])
        end_price = float(close_prices.iloc[-1])

        if np.isnan(start_price) or np.isnan(end_price) or start_price <= 0:
            return 0.08, "Calculation error (Default 8.0%)"
        cagr = (end_price / start_price) ** (1.0 / lookback_years) - 1.0
        if np.isnan(cagr):
            return 0.08, "Default to 8.0%"
        return float(cagr), f"Historical CAGR: {cagr:.2%}"
    except Exception:
        return 0.08, "Fetch error (Default 8.0%)"


# 3. Session State (Stores custom ad-hoc cash injections)
if "injections" not in st.session_state:
    st.session_state.injections = []

# 4. Sidebar: Multi Stock Asset Builder
popular_tickers = ["SPY", "QQQ", "VOO", "VWRA.L", "CSPX.L", "VT", "SMH",
    "NVDA", "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "AMD"]
if "ticker_pool" not in st.session_state:
    st.session_state.ticker_pool = popular_tickers
selected_tickers = st.sidebar.multiselect(
    "Select Stocks / ETFs to Invest In:",
    options=popular_tickers,
    default=[],
    help="You can also type any custom ticker from Yahoo Finance!"
)

if not selected_tickers:
    st.warning("Please select atleast one stock/ETF to begin")
    st.stop()

lookback = st.sidebar.selectbox("Historical Lookback Window", [3, 5, 10], index=1)
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 5)
total_months = horizon_years * 12

# SMART RISK: MEAN REVERSION TOGGLE
st.sidebar.markdown("---")
st.sidebar.header("🧠 Smart Risk Engine")
enable_mean_reversion = st.sidebar.checkbox(
    "Apply Mean Reversion",
    value=True,
    help="Caps extreme historic rates (like NVDA 47%) to a sustainable long-term ceiling."
)
# ✅ Interactive Mean Reversion Ceiling Slider
MAX_REALISTIC_CAGR = st.sidebar.slider(
    "Max Realistic Growth Ceiling (%)",
    min_value=12.0,
    max_value=30.0,
    value=20.0,
    step=1.0,
    help="Caps hyper-growth stocks to this ceiling so 5 to 10 years projections remain realistic."
) / 100.0

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
        suggested_forward_rate = min(raw_rate, 0.18) if enable_mean_reversion else raw_rate

        # 2. Per-Stock Forward Return Input:
        forward_cagr = st.number_input(
            f"Expected Future CAGR (%/yr)",
            min_value=1.0,
            max_value=100.0,
            value=float(round(suggested_forward_rate * 100, 2)),
            format="%.2f",
            step=0.5,
            key=f"cagr_{ticker}",
            help=f"Historic was {raw_rate * 100:.1f}%. Adjust what you expect {ticker} to do over your horizon."
        ) / 100.0

        # Smart Default Suggestion
        is_capped = enable_mean_reversion and raw_rate > 0.18
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

        c1, c2 = st.columns(2)
        with c1:
            init_val = st.number_input(f"Initial $", min_value=0.0, value=0.0, step=50.0, key=f"init_{ticker}")
        with c2:
            month_val = st.number_input(f"Monthly $", min_value=0.0, value=0.0, step=25.0, key=f"month_{ticker}")

            # --- ⚡ TWO-STAGE GROWTH ENGINE ---
            is_hyper_growth = raw_rate > 0.25  # Automatically checks if stock is crazy hot like NVDA

            use_two_stage = st.checkbox(
                f"⚡ Two-Stage Growth (High Momentum → Mature)",
                value=is_hyper_growth,
                key=f"twostage_{ticker}",
                help="Models high growth for the next few years, followed by a gradual slowdown."
            )

            if use_two_stage:
                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    stage1_years = st.slider(
                        "Momentum Years (Stage 1)",
                        min_value=1, max_value=min(horizon_years, 7), value=3,
                        key=f"s1_yrs_{ticker}"
                    )
                    stage1_rate = st.number_input(
                        "Stage 1 CAGR (%/yr)",
                        min_value=5.0, max_value=60.0,
                        value=float(round(raw_rate * 100 * 0.75, 1)),  # Suggests ~35% for NVDA
                        step=1.0, key=f"s1_rate_{ticker}"
                    ) / 100.0
                with col_s2:
                    st.caption(f"**Stage 2 (Years {stage1_years + 1} to {horizon_years})**")
                    stage2_rate = st.number_input(
                        "Stage 2 Mature CAGR (%/yr)",
                        min_value=5.0, max_value=30.0, value=18.0,
                        step=0.5, key=f"s2_rate_{ticker}"
                    ) / 100.0
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

# PRIVACY: SAVE / RESTORE PROFILE TO LAPTOP
st.sidebar.markdown("---")
st.sidebar.subheader("💾 Backup & Restore (Privacy Safe)")

# a) Download personal portfolio to your own Mac
user_export_data = json.dumps({
    "tickers": selected_tickers,
    "allocations": {t: {"initial": asset_config[t]["initial"], "monthly": asset_config[t]["monthly"]} for t in
                    selected_tickers},
    "injections": st.session_state.injections
}, indent=4)

st.sidebar.download_button(
    label="📥 Download My Portfolio (.json)",
    data=user_export_data,
    file_name="my_portfolio.json",
    mime="application/json",
    help="Saves your exact portfolio directly to your laptop so nobody else can see it."
)

# b) Upload file when visiting in the future
uploaded_profile = st.sidebar.file_uploader("📤 Restore from File", type=["json"])
if uploaded_profile is not None:
    try:
        profile_data = json.load(uploaded_profile)
        st.session_state.injections = profile_data.get("injections", [])
        st.sidebar.success("Profile Restored! Re-running...")
    except Exception:
        st.sidebar.error("Invalid portfolio file.")


# 5. AD-HOC CASH INJECTION SIMULATOR (The "What-If" Engine)
# ---------------------------------------------------------
st.title("💼 Apex Multi-Asset Wealth Modeler")
st.caption(
    f"Projecting cashflow across {len(selected_tickers)} assets over a **{horizon_years}-Year ({total_months} Months)** timeline.")

with st.expander("⚡ Simulate an Ad-Hoc Cash Injection (The 'What-If' Tool)", expanded=True):
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

# Display current active injections
if st.session_state.injections:
    with st.expander("📋 Current Active Injections (Click to View / Clear)"):
        inj_df = pd.DataFrame(st.session_state.injections)
        st.dataframe(inj_df, use_container_width=True)
        if st.button("🗑️ Clear All Injections"):
            st.session_state.injections = []
            st.rerun()

# ---------------------------------------------------------
# 6. MULTI-ASSET RECURSIVE COMPOUNDING ENGINE
# ---------------------------------------------------------
dates_timeline = [START_DATE + relativedelta(months=i) for i in range(total_months + 1)]

# Pre-process injections into a quick lookup: {(ticker, month): total_amount}
injection_map = {}
for item in st.session_state.injections:
    key = (item["Ticker"], item["Month"])
    injection_map[key] = injection_map.get(key, 0.0) + item["Amount"]

# Tracking balances per ticker over time
all_active_tickers = list(asset_config.keys())
asset_histories = {ticker: [asset_config[ticker]["initial"]] for ticker in all_active_tickers}
current_balances = {ticker: asset_config[ticker]["initial"] for ticker in all_active_tickers}
cost_basis_history = [total_initial_cash]
running_cost = total_initial_cash

# Current balances
current_balances = {ticker: asset_config[ticker]["initial"] for ticker in selected_tickers}

for m in range(1, total_months + 1):
    month_total_deposit = 0.0

    for ticker in all_active_tickers:
        cfg = asset_config[ticker]
        for ticker in all_active_tickers:
            cfg = asset_config[ticker]

            # 🧠 DYNAMIC TWO-STAGE SELECTION:
            # If within Stage 1, use high momentum rate. If passed Stage 1, switch to mature rate!
            if m <= cfg.get("stage1_months", total_months):
                r = cfg.get("stage1_monthly_r", cfg.get("monthly_r", 0.0))
            else:
                r = cfg.get("stage2_monthly_r", cfg.get("monthly_r", 0.0))

            # 1. Money makes money (compound interest)
            current_balances[ticker] *= (1 + r)

        # 1. Money makes money (compound interest)
        current_balances[ticker] *= (1 + r)

        # 2. Add regular monthly inflow
        current_balances[ticker] += cfg["monthly"]
        month_total_deposit += cfg["monthly"]

        # 3. Add ad-hoc injection if present for this ticker & month
        if (ticker, m) in injection_map:
            extra = injection_map[(ticker, m)]
            current_balances[ticker] += extra
            month_total_deposit += extra

        # Record history
        asset_histories[ticker].append(current_balances[ticker])

    running_cost += month_total_deposit
    cost_basis_history.append(running_cost)

# Build total portfolio trajectory
portfolio_history = [sum(asset_histories[ticker][i] for ticker in selected_tickers) for i in range(total_months + 1)]

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


