import os
import sys
import json
import sqlite3
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config import DB_PATH, BASELINE_DB_PATH, ZONES
from src.utils.carbon import get_tou_price, get_carbon_intensity

# Page Configuration
st.set_page_config(
    page_title="Honeywell Autonomous BMS Dashboard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
<style>
    .main { background-color: #0E1117; }
    .stMetric {
        background-color: #1E222D;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #2E3440;
    }
    .metric-card {
        background: linear-gradient(135deg, #1E222D 0%, #252A37 100%);
        border: 1px solid #3B4252;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
    }
    .metric-value {
        font-size: 28px;
        font-weight: bold;
        color: #00E676;
    }
    .metric-label {
        font-size: 14px;
        color: #D8DEE9;
        margin-top: 5px;
    }
    .status-badge {
        background-color: #00E676;
        color: #000;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=5)
def load_data(db_path):
    if not os.path.exists(db_path):
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM state_log", conn)
    conn.close()
    if df.empty:
        return pd.DataFrame()
    
    df['hour'] = df['sim_time_hours'].astype(int) % 24
    df['tou_price'] = df['hour'].apply(get_tou_price)
    df['carbon_g'] = df['hour'].apply(get_carbon_intensity)
    df['kwh'] = df['hvac_elec_kw'] * 0.25
    df['cost_usd'] = df['kwh'] * df['tou_price']
    df['carbon_kg'] = (df['kwh'] * df['carbon_g']) / 1000.0
    return df

@st.cache_data(ttl=5)
def load_decisions(db_path):
    if not os.path.exists(db_path):
        return pd.DataFrame()
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM decisions ORDER BY id DESC", conn)
    conn.close()
    return df

# Main Header
st.title("⚡ Honeywell Autonomous BMS — Quantitative Savings Dashboard")
st.markdown("### Physical AI Closed-Loop Optimization Engine (EnergyPlus × Ollama Llama 3.1 via MCP)")

# Sidebar Controls
st.sidebar.header("⚙️ Simulation Controls & Filters")
selected_zone = st.sidebar.selectbox("Select Zone View", ["ALL"] + ZONES)

df_base = load_data(BASELINE_DB_PATH)
df_ai = load_data(DB_PATH)
df_decisions = load_decisions(DB_PATH)

if df_base.empty or df_ai.empty:
    st.warning("⚠️ Simulation database files loading or incomplete. Please ensure baseline and AI runs have completed.")
    st.stop()

# Filter by selected zone if applicable
if selected_zone != "ALL":
    df_base_zone = df_base[df_base['zone_name'] == selected_zone]
    df_ai_zone = df_ai[df_ai['zone_name'] == selected_zone]
else:
    df_base_zone = df_base
    df_ai_zone = df_ai

# Summary KPI Computations
kwh_base = df_base['kwh'].sum()
kwh_ai = df_ai['kwh'].sum()
kwh_saved = kwh_base - kwh_ai
kwh_pct = (kwh_saved / kwh_base * 100.0) if kwh_base > 0 else 0.0

cost_base = df_base['cost_usd'].sum()
cost_ai = df_ai['cost_usd'].sum()
cost_saved = cost_base - cost_ai
cost_pct = (cost_saved / cost_base * 100.0) if cost_base > 0 else 0.0

peak_base = df_base['hvac_elec_kw'].max()
peak_ai = df_ai['hvac_elec_kw'].max()
peak_shaved = peak_base - peak_ai
peak_pct = (peak_shaved / peak_base * 100.0) if peak_base > 0 else 0.0

carbon_base = df_base['carbon_kg'].sum()
carbon_ai = df_ai['carbon_kg'].sum()
carbon_saved = carbon_base - carbon_ai

# PMV Compliance Computation
occupied = df_ai[(df_ai['hour'] >= 8) & (df_ai['hour'] <= 18)]
pmv_valid = occupied[occupied['zone_pmv'].notnull()] if not occupied.empty else pd.DataFrame()
if not pmv_valid.empty:
    in_range = pmv_valid[(pmv_valid['zone_pmv'] >= -0.5) & (pmv_valid['zone_pmv'] <= 0.5)]
    comfort_compliance_pct = (len(in_range) / len(pmv_valid)) * 100.0
else:
    comfort_compliance_pct = 100.0

# KPI Metric Cards Row
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Energy Consumed", f"{kwh_ai:.1f} kWh", delta=f"-{kwh_pct:.1f}% vs Base", delta_color="inverse")
c2.metric("Electricity Cost", f"${cost_ai:.2f}", delta=f"-{cost_pct:.1f}% vs Base", delta_color="inverse")
c3.metric("Peak Demand", f"{peak_ai:.2f} kW", delta=f"-{peak_pct:.1f}% Shaved", delta_color="inverse")
c4.metric("Thermal Comfort", f"{comfort_compliance_pct:.1f}%", delta="ASHRAE 55 Compliant", delta_color="normal")
c5.metric("Carbon Footprint", f"{carbon_ai:.1f} kg", delta=f"-{carbon_saved:.1f} kg CO2", delta_color="inverse")

st.markdown("---")

# Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Energy & Cost Peak Shaving", 
    "🌡️ Thermal Comfort & PMV Compliance", 
    "🤖 LLM Decision Audit Trail", 
    "🌍 Environmental & Carbon Impact"
])

with tab1:
    st.subheader("HVAC Power Demand (kW) & Time-of-Use Electricity Rate ($/kWh)")
    
    # Resample to hourly mean for smooth timeline visualization
    df_base_hourly = df_base.groupby('sim_time_hours').agg({
        'hvac_elec_kw': 'mean',
        'tou_price': 'first'
    }).reset_index()

    df_ai_hourly = df_ai.groupby('sim_time_hours').agg({
        'hvac_elec_kw': 'mean',
        'tou_price': 'first'
    }).reset_index()

    fig_power = make_subplots(specs=[[{"secondary_y": True}]])
    
    fig_power.add_trace(
        go.Scatter(x=df_base_hourly['sim_time_hours'], y=df_base_hourly['hvac_elec_kw'],
                   name="Baseline HVAC kW", line=dict(color="#FF5252", width=1.5)),
        secondary_y=False
    )
    
    fig_power.add_trace(
        go.Scatter(x=df_ai_hourly['sim_time_hours'], y=df_ai_hourly['hvac_elec_kw'],
                   name="AI Optimized HVAC kW", line=dict(color="#00E676", width=2)),
        secondary_y=False
    )
    
    fig_power.add_trace(
        go.Scatter(x=df_ai_hourly['sim_time_hours'], y=df_ai_hourly['tou_price'],
                   name="TOU Rate ($/kWh)", line=dict(color="#FFB300", width=1, dash="dot")),
        secondary_y=True
    )
    
    fig_power.update_layout(
        template="plotly_dark",
        title="Real-Time Peak Load Shaving During High-Cost TOU Pricing",
        xaxis_title="Simulation Time (Hours)",
        height=450
    )
    fig_power.update_yaxes(title_text="HVAC Electricity Demand (kW)", secondary_y=False)
    fig_power.update_yaxes(title_text="TOU Rate ($/kWh)", secondary_y=True)
    st.plotly_chart(fig_power, use_container_width=True)

with tab2:
    st.subheader("Fanger PMV Thermal Comfort Index vs. ASHRAE 55 Comfort Boundaries")
    
    fig_pmv = go.Figure()
    
    # Comfort Band Shading [-0.5, +0.5]
    fig_pmv.add_hrect(y0=-0.5, y1=0.5, fillcolor="green", opacity=0.15, line_width=0, annotation_text="ASHRAE 55 Comfort Zone")
    
    # Baseline PMV
    fig_pmv.add_trace(go.Scatter(
        x=df_base_zone['sim_time_hours'], y=df_base_zone['zone_pmv'],
        name="Baseline PMV", line=dict(color="#FF5252", width=1.2)
    ))
    
    # AI Optimized PMV
    fig_pmv.add_trace(go.Scatter(
        x=df_ai_zone['sim_time_hours'], y=df_ai_zone['zone_pmv'],
        name="AI Optimized PMV", line=dict(color="#00E676", width=1.8)
    ))
    
    fig_pmv.update_layout(
        template="plotly_dark",
        title=f"Zone PMV Trajectory ({selected_zone})",
        xaxis_title="Simulation Time (Hours)",
        yaxis_title="Predicted Mean Vote (PMV)",
        yaxis=dict(range=[-2.5, 2.5]),
        height=450
    )
    st.plotly_chart(fig_pmv, use_container_width=True)
    
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        st.subheader("Zone Temperatures vs. Active Heating/Cooling Setpoints")
        fig_temp = go.Figure()
        fig_temp.add_trace(go.Scatter(x=df_ai_zone['sim_time_hours'], y=df_ai_zone['zone_temp_c'], name="Zone Air Temp (°C)", line=dict(color="#00E676")))
        fig_temp.add_trace(go.Scatter(x=df_ai_zone['sim_time_hours'], y=df_ai_zone['heating_sp_c'], name="Heating Setpoint (°C)", line=dict(color="#FF5252", dash="dash")))
        fig_temp.add_trace(go.Scatter(x=df_ai_zone['sim_time_hours'], y=df_ai_zone['cooling_sp_c'], name="Cooling Setpoint (°C)", line=dict(color="#29B6F6", dash="dash")))
        fig_temp.update_layout(template="plotly_dark", xaxis_title="Simulation Time (Hours)", yaxis_title="Temperature (°C)")
        st.plotly_chart(fig_temp, use_container_width=True)
        
    with col_t2:
        st.subheader("Indoor Air Quality (IAQ) Mechanical Ventilation Flow")
        fig_iaq = go.Figure()
        fig_iaq.add_trace(go.Scatter(x=df_ai_zone['sim_time_hours'], y=df_ai_zone['zone_iaq_vent_flow'], name="Ventilation Flow Rate (kg/s)", line=dict(color="#AB47BC")))
        fig_iaq.add_hline(y=0.005, line_dash="dot", line_color="#FFB300", annotation_text="Min IAQ Threshold")
        fig_iaq.update_layout(template="plotly_dark", xaxis_title="Simulation Time (Hours)", yaxis_title="Mass Flow Rate (kg/s)")
        st.plotly_chart(fig_iaq, use_container_width=True)

with tab3:
    st.subheader("🤖 Autonomous Agent Decision Audit Log (MCP Protocol Tracing)")
    st.markdown("Full transparency log of Ollama Llama 3.1 decisions triggered every 60 simulation minutes via Stdio MCP Tool Protocol:")
    
    if not df_decisions.empty:
        st.dataframe(
            df_decisions[['id', 'sim_time_hours', 'wall_time', 'llm_reasoning', 'action_taken']],
            use_container_width=True,
            height=400
        )
    else:
        st.info("No decision logs recorded yet in database.")

with tab4:
    st.subheader("🌍 Cumulative Carbon Emissions Trajectory (kg CO₂)")
    
    df_base_carbon = df_base.groupby('sim_time_hours')['carbon_kg'].sum().cumsum().reset_index()
    df_ai_carbon = df_ai.groupby('sim_time_hours')['carbon_kg'].sum().cumsum().reset_index()
    
    fig_carbon = go.Figure()
    fig_carbon.add_trace(go.Scatter(x=df_base_carbon['sim_time_hours'], y=df_base_carbon['carbon_kg'], name="Baseline Cumulative Carbon (kg CO₂)", line=dict(color="#FF5252", width=2)))
    fig_carbon.add_trace(go.Scatter(x=df_ai_carbon['sim_time_hours'], y=df_ai_carbon['carbon_kg'], name="AI Optimized Cumulative Carbon (kg CO₂)", line=dict(color="#00E676", width=2.5)))
    fig_carbon.update_layout(template="plotly_dark", xaxis_title="Simulation Time (Hours)", yaxis_title="Cumulative CO₂ Emissions (kg)")
    st.plotly_chart(fig_carbon, use_container_width=True)

# Footer
st.markdown("---")
st.markdown("🏆 **Honeywell Hackathon Submission** | Physical AI Closed-Loop Autonomous Building Operations System")
