import streamlit as st  # Turns code into websites
import pandas as pd
import plotly.express as px  # Draw nice interactive line charts
import plotly.graph_objects as go
import numpy as np

# 1. Page Styling and Configuration
st.set_page_config(
    page_title="Wealth Simulator",
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
        padding: 18px;
        border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .metric-label { font-size: 0.85rem; color: #6c757d; font-weight: 600; text-transform: uppercase; }
    .metric-value { font-size: 1.6rem; color: #212529; font-weight: 700; margin-top: 4px; }
    </style>
""", unsafe_allow_html=True)

# 2. The Math
def calculate_future_value(principal: float, monthly_deposit: float,
                           annual_rate: float, months: int):
    """Computes compound growth using vectorized closed-form financial
    equations.
       Formula: FV = P * (1+r)^t + PMT * [((1+r)^t-1) / r]
    """
    t = np.arange(1, months + 1)
    r = annual_rate / 12

    if r == 0:
        fv = principal + (monthly_deposit * t)
    else:
        fv_lump_sum = principal * (1 + r) ** t
        fv_annuity = monthly_deposit * (((1 + r) ** t) - 1) / r
        fv = fv_lump_sum + fv_annuity

    cumulative_deposits = principal + (monthly_deposit * t)
    return t, fv, cumulative_deposits

# 3. Sidebar: User Input Engine
st.sidebar.header("🕹️ Capital & Cash Flow")

# Starting Capital
initial_capital = st.sidebar.number_input(
    "Starting Capital (SGD)",
    min_value=0.0,
    value=None,
    placeholder="Type any amount",
    step=1.0,
    help="Type in your exact starting cash"
)

# Monthly Inflow
monthly_inflow = st.sidebar.number_input(
    "Monthly Contributions (SGD)",
    min_value=0.0,
    value=None,
    placeholder="Type monthly investments amt",
    step=1.0,
    help="Type in how much you plan to invest monthly"
)

initial_capital = initial_capital if initial_capital is None else 0.0  # Prevent crash from no input (None)
monthly_inflow = monthly_inflow if monthly_inflow is not None else 0.0


# Duration
horizon_years = st.sidebar.slider(
    "Time Horizon (Years)",
    min_value=1,
    max_value=50,
    value=15
)

st.sidebar.markdown("---")
st.sidebar.header("⚙️ Macro Assumptions")
adjust_inflation = st.sidebar.checkbox("Adjust for Inflation (real value)", value=False)
inflation_rate = 0.025 if adjust_inflation else 0.0  # Assumes 2.5%

# 4. Main Page : Asset Allocation Set-Up
st.title("💼 Institutional Portfolio Modeler")
st.caption("Design your Core-Satellite strategy and visualize long-term compounding")

st.subheader("1. COnfigure Asset Weights and Yields")
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("**Core: Global ETF (e.g. VWRA)**")
    core_weight = st.slider("Weight (%)", 0, 100, 80, key='core_w') / 100.0  # Unsure
    core_return = st.number_input("Expected Return (%/yr)", value=9.5, step=0.5) / 100.0

with col2:
    st.markdown("**Satellite: HIgh-Growth Tech (e.g. NVDA/GOOGL)**")
    satellite_weight = st.slider("Weight (%)", 0, 100, 20, key="sat_w") / 100.0
    satellite_return = st.number_input("Expected Return (%/yr)", value = 14.0, step=0.5) / 100.0

with col3:
     st.markdown("**Benchmark: Risk-Free / Cash **")
     cash_return = st.number_input("Bank/Cash Yield (%/yr)", value=2.5, step=0.25) / 100.0

# Calculate Weighted Blended Rate
total_weight = core_weight + satellite_weight
if not np.isclose(total_weight, 1.0):
    st.warning(f"⚠️ Allocation weights must sum to 100% Current sum: {total_weight * 100:.0f}%")

effective_annual_rate = (core_weight * core_return) + (satellite_weight * satellite_return) - inflation_rate
effective_cash_rate = cash_return - inflation_rate

# 5. Data Computation
total_months = horizon_years * 12
timeline_months, portfolio_vals, total_deposits = calculate_future_value(
    initial_capital, monthly_inflow, effective_annual_rate, total_months
)
_, cash_vals,_ = calculate_future_value(initial_capital, monthly_inflow, effective_cash_rate, total_months)
final_balance = portfolio_vals[-1]
final_invested = total_deposits[-1]
total_gains = final_balance - final_invested
roi_pct = (total_gains / final_invested) * 100

# 6. KPI Dashboard Metrics
st.subheader("2. Performance Overview")
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Invested</div>
                <div class="metric-value">${final_invested:,.0f}</div>
            </div>
        """, unsafe_allow_html=True)
with m2:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Estimated Final Wealth</div>
            <div class="metric-value" style="color: #0d6efd;">${final_balance:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
with m3:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Pure Compound Gains</div>
            <div class="metric-value" style="color: #198754;">+${total_gains:,.0f}</div>
        </div>
    """, unsafe_allow_html=True)
with m4:
    st.markdown(f"""
        <div class="metric-card">
            <div class="metric-label">Return on Investment (ROI)</div>
            <div class="metric-value" style="color: #198754;">+{roi_pct:.1f}%</div>
        </div>
    """, unsafe_allow_html=True)

st.write("")

# 7. Visualization
tab1, tab2, tab3 = st.tabs(["📈 Growth Trajectory", "📊 Principal vs. Profit Breakdown", "🎯 Wealth Milestones"])
years_axis = timeline_months / 12

with tab1:
    fig = go.Figure()

    # Portfolio Trajectory
    fig.add_trace(go.Scatter(
        x=years_axis, y=portfolio_vals,
        mode='lines', name=f'Custom Portfolio ({(effective_annual_rate * 100):.1f}%)',
        line=dict(color='#0d6efd', width=3)
    ))

    # Cash / Risk Free
    fig.add_trace(go.Scatter(
        x=years_axis, y=cash_vals,
        mode='lines', name=f'Cash Alternative ({(effective_cash_rate * 100):.1f}%)',
        line=dict(color='#6c757d', width=2, dash='dot')
    ))

    # Total Principal
    fig.add_trace(go.Scatter(
        x=years_axis, y=total_deposits,
        mode='lines', name='Deposited Capital',
        line=dict(color='#adb5bd', width=1.5, dash='dash')
    ))

    fig.update_layout(
        title="Projected Capital Growth Over Time",
        xaxis_title="Years",
        yaxis_title="Account Balance (SGD)",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    # Stacked Area Chart (Principal vs Returns)
    fig_area = go.Figure()
    pure_growth = portfolio_vals - total_deposits

    fig_area.add_trace(go.Scatter(
        x=years_axis, y=total_deposits,
        mode='lines', stackgroup='one',
        name='Principal Invested',
        line=dict(width=0.5, color='#a0c4ff')
    ))
    fig_area.add_trace(go.Scatter(
        x=years_axis, y=pure_growth,
        mode='lines', stackgroup='one',
        name='Compound Interest',
        line=dict(width=0.5, color='#38b000')
    ))

    fig_area.update_layout(
        title="Portfolio Composition: Money In vs. Money Made",
        xaxis_title="Years",
        yaxis_title="Total Value (SGD)",
        hovermode="x unified",
        template="plotly_white"
    )
    st.plotly_chart(fig_area, use_container_width=True)

with tab3:
    st.write("#### Journey to Your First $100,000 SGD")
    target = 100000.0
    hit_idx = np.where(portfolio_vals >= target)[0]

    if len(hit_idx) > 0:
        first_month = hit_idx[0] + 1
        hit_year = first_month // 12
        hit_rem_months = first_month % 12
        st.success(
            f"🚀 At this pace, you will surpass **$100,000 SGD** in **{hit_year} years and {hit_rem_months} months**!")

        # Show breakdown at milestone
        milestone_invested = total_deposits[hit_idx[0]]
        st.write(f"- **Your actual cash contributions:** `${milestone_invested:,.2f}`")
        st.write(f"- **Free money from the market:** `${target - milestone_invested:,.2f}`")
    else:
        st.info(
            f"Target of $100,000 not reached within the chosen {horizon_years}-year window. Try extending the horizon or increasing your monthly savings!")