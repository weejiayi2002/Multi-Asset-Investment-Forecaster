import streamlit as st  # Turns code into websites
import pandas as pd
import plotly.express as px  # Draw nice interactive line charts
import plotly.graph_objects as go
from datetime import datetime
from dateutil.relativedelta import relativedelta
import yfinance as yf
import numpy as np

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
        background-color: #e8f5e9;
        border-left: 5px solid #2e7d32;
        padding: 12px;
        border-radius: 6px;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

start_date = datetime.today()

# 2. Yahoo Finance Live Engine
@st.cache_data(ttl=8640)
def fetch_stock_cagr(ticker: str, lookback_years: int = 5):
    """Fetches real historical prices and computes annualized CAGR"""
    try:
        data = yf.download(ticker, period=f"{lookback_years}y", progress=False)
        if data.empty or len(data) < 20:
            return 0.08, "Data unvailable (Default 8.0%)"

        close_prices = data["Close"]
        if isinstance(close_prices, pd.DataFrame):
            close_prices = close_prices.iloc[:, 0]

        start_price = float(close_prices.iloc[0])
        end_price = float(close_prices.iloc[-1])
        cagr = (end_price / start_price) ** (1.0 / lookback_years) - 1.0
        return cagr, f"{lookback_years}Y Hist. CAGR: {cagr * 100:.1f}%"
    except Exception:
        return 0.08, "Fetch Error (Default 8.0%)"

# 3. Session State (Stores custom ad-hoc cash injections)
if "injections" not in st.session_state:
    st.session_state.injections = [
        {"Ticker" : "NVDA", "Month": 4, "Amount": 2000.0, "Note": "Tuition Freelance"}
    ]

# 4. Sidebar: Multi Stock Asset Builder
popular_tickers = ["VWRA.L", "SPY", "NVDA", "AAPL", "GOOGL", "MSFT", "TSLA", "AMZN"]
selected_tickers = st.sidebar.multiselect(
    "Select Stocks / ETFs to Invest In:",
    options=popular_tickers,
    default=["SPY", "NVDA", "AAPL"],
    help="You can also type any custom ticker from Yahoo Finance!"
)

if not selected_tickers:
    st.warning("Please select atleast one stock/ETF to begin")
    st.stop()

lookback = st.sidebar.selectbox("Historical Lookback Window", [3, 5, 10], index=1)
horizon_years = st.sidebar.slider("Investment Horizon (Years)", 1, 30, 5)
total_months = horizon_years * 12

st.sidebar.markdown("---")
st.sidebar.header("💵 Starting and Monthly Allocation")

# Collect individual stock allocations
asset_config = {}
total_initial_cash = 0
total_monthly_cash = 0

for ticker in selected_tickers:
    with st.sidebar.expander(f"📌 {ticker} Allocation", expanded=True):
        rate, msg = fetch_stock_cagr(ticker, lookback)
        st.caption(f"📈 {msg}")

        c1, c2 = st.columns(2)

        with c1:
            init_val = st.number_input(f"Initial $ ({ticker})",
            min_value = 0.0, value=2000.0, step=100.0, key=f"init_{ticker}")

            with c2:
                month_val = st.number_input(f"Monthly $ ({ticker})", min_value=0.0, value=100.0, step=25.0,
                                            key=f"month_{ticker}")

            asset_config[ticker] = {
                "cagr": rate,
                "monthly_r": rate / 12.0,
                "initial": init_val,
                "monthly": month_val
            }
            total_initial_cash += init_val
            total_monthly_cash += month_val

    st.sidebar.info(
        f"**Total Capital Today:** ${total_initial_cash:,.0f} SGD\n\n**Total Monthly Flow:** ${total_monthly_cash:,.0f} SGD/mo")

# 5. Cash Injections
# 5. AD-HOC CASH INJECTION SIMULATOR (The "What-If" Engine)
# ---------------------------------------------------------
st.title("💼 Apex Multi-Asset Wealth Modeler")
st.caption(
    f"Projecting cashflow across {len(selected_tickers)} assets over a **{horizon_years}-Year ({total_months} Months)** timeline.")

with st.expander("⚡ Simulate an Ad-Hoc Cash Injection (The 'What-If' Tool)", expanded=True):
    col_a, col_b, col_c, col_d = st.columns(4)

    with col_a:
        inj_ticker = st.selectbox("Target Stock", selected_tickers)
    with col_b:
        inj_month = st.number_input("In Which Month?", min_value=1, max_value=total_months, value=4)
    with col_c:
        inj_amount = st.number_input("Injection Amount ($)", min_value=100.0, value=2000.0, step=100.0)
    with col_d:
        inj_note = st.text_input("Reason / Note", value="Internship Pay")

    # Math: What is the isolated impact of this single injection?
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
asset_histories = {ticker: [asset_config[ticker]["initial"]] for ticker in selected_tickers}
cost_basis_history = [total_initial_cash]
running_cost = total_initial_cash

# Current balances
current_balances = {ticker: asset_config[ticker]["initial"] for ticker in selected_tickers}

for m in range(1, total_months + 1):
    month_total_deposit = 0.0

    for ticker in selected_tickers:
        cfg = asset_config[ticker]
        r = cfg["monthly_r"]

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


