import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import time

# ─── Config ────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

# ─── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SafeWatch — Construction Safety Monitor",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0d1117; color: #e6edf3; }
    [data-testid="stSidebar"] { background-color: #161b22; border-right: 1px solid #21262d; }
    .metric-card { background: #161b22; border: 1px solid #21262d; border-radius: 8px; padding: 20px 24px; position: relative; overflow: hidden; }
    .metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 3px; height: 100%; }
    .metric-card.danger::before  { background: #f85149; }
    .metric-card.warning::before { background: #d29922; }
    .metric-card.safe::before    { background: #3fb950; }
    .metric-card.info::before    { background: #388bfd; }
    .metric-label { font-size: 11px; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; color: #8b949e; margin-bottom: 8px; }
    .metric-value { font-family: 'JetBrains Mono', monospace; font-size: 32px; font-weight: 600; color: #e6edf3; line-height: 1; }
    .metric-sub { font-size: 12px; color: #8b949e; margin-top: 6px; }
    .alert-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }
    .badge-critical { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
    .badge-warning  { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
    .badge-safe     { background: rgba(63,185,80,0.15);  color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
    .section-header { font-size: 11px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: #8b949e; border-bottom: 1px solid #21262d; padding-bottom: 8px; margin-bottom: 16px; }
    .live-dot { display: inline-block; width: 8px; height: 8px; background: #f85149; border-radius: 50%; margin-right: 6px; animation: pulse 1.5s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; }
</style>
""", unsafe_allow_html=True)


# ─── API helpers ───────────────────────────────────────────────────────────────
def fetch_stats():
    try:
        r = requests.get(f"{API_BASE}/violations/stats", timeout=3)
        return r.json()
    except:
        return None

def fetch_violations(limit=50, zone=None, violation=None):
    try:
        params = {"limit": limit}
        if zone and zone != "All":
            params["zone"] = zone
        if violation and violation != "All":
            params["violation"] = violation
        r = requests.get(f"{API_BASE}/violations", params=params, timeout=3)
        return r.json()
    except:
        return []

def fetch_zones():
    try:
        r = requests.get(f"{API_BASE}/zones", timeout=3)
        return ["All"] + r.json()
    except:
        return ["All"]


# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🦺 SafeWatch")
    st.markdown("<div style='color:#8b949e;font-size:12px;margin-bottom:24px'>Construction Safety Monitor</div>", unsafe_allow_html=True)
    st.markdown("**Filters**")
    zones = fetch_zones()
    selected_zone = st.selectbox("Zone", zones)
    selected_type = st.selectbox("Violation Type", ["All", "No Hardhat", "No Safety Vest"])
    limit = st.slider("Max Records", 10, 200, 50)
    st.markdown("---")
    st.markdown("**Auto-refresh**")
    auto_refresh = st.toggle("Enable", value=True)
    refresh_rate = st.selectbox("Interval", ["5s", "10s", "30s"])
    st.markdown("---")
    if st.button("🗑 Clear DB (Dev Only)", type="secondary"):
        import sqlite3
        conn = sqlite3.connect("backend/violations.db")
        conn.execute("DELETE FROM violations")
        conn.commit()
        conn.close()
        st.success("DB cleared")
        st.rerun()
    st.caption("Model: YOLOv8n  |  Backend: FastAPI")
    st.caption(f"API: {API_BASE}")


# ─── Fetch data ────────────────────────────────────────────────────────────────
stats      = fetch_stats()
violations = fetch_violations(
    limit=limit,
    zone=selected_zone if selected_zone != "All" else None,
    violation=selected_type if selected_type != "All" else None
)
api_online = stats is not None

# ─── Header ────────────────────────────────────────────────────────────────────
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("## Construction Site Safety Monitor")
    st.markdown(f"<span class='live-dot'></span><span style='color:#8b949e;font-size:13px'>{'LIVE' if api_online else 'API OFFLINE'} — {datetime.now().strftime('%d %b %Y, %H:%M:%S')}</span>", unsafe_allow_html=True)
with col_status:
    if not api_online:
        badge, label = "badge-warning", "API OFFLINE"
    elif stats and stats.get("unacknowledged", 0) > 0:
        badge, label = "badge-critical", "VIOLATIONS DETECTED"
    else:
        badge, label = "badge-safe", "ALL CLEAR"
    st.markdown(f"<div style='text-align:right;margin-top:16px'><span class='alert-badge {badge}'>{label}</span></div>", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ─── Metric cards ──────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
total       = stats.get("total", 0) if stats else 0
unacked     = stats.get("unacknowledged", 0) if stats else 0
no_hardhat  = stats.get("no_hardhat", 0) if stats else 0
no_vest     = stats.get("no_vest", 0) if stats else 0
today_count = stats.get("today", 0) if stats else 0

with m1:
    st.markdown(f'<div class="metric-card danger"><div class="metric-label">Active Violations</div><div class="metric-value">{unacked}</div><div class="metric-sub">Unacknowledged alerts</div></div>', unsafe_allow_html=True)
with m2:
    st.markdown(f'<div class="metric-card warning"><div class="metric-label">Today\'s Incidents</div><div class="metric-value">{today_count}</div><div class="metric-sub">Since midnight</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card danger"><div class="metric-label">No Hardhat</div><div class="metric-value">{no_hardhat}</div><div class="metric-sub">Helmet violations</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card warning"><div class="metric-label">No Safety Vest</div><div class="metric-value">{no_vest}</div><div class="metric-sub">Vest violations</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ─── Charts ────────────────────────────────────────────────────────────────────
chart1, chart2 = st.columns(2)

with chart1:
    st.markdown("<div class='section-header'>Violations by Zone</div>", unsafe_allow_html=True)
    if stats and stats.get("by_zone"):
        zone_df = pd.DataFrame(stats["by_zone"])
        fig = px.bar(zone_df.sort_values("count", ascending=True), x="count", y="zone", orientation="h",
                     color="count", color_continuous_scale=["#388bfd", "#d29922", "#f85149"])
        fig.update_layout(plot_bgcolor="#161b22", paper_bgcolor="#161b22", font_color="#8b949e",
                          showlegend=False, coloraxis_showscale=False,
                          margin=dict(l=0, r=0, t=0, b=0),
                          xaxis=dict(gridcolor="#21262d", title=""),
                          yaxis=dict(gridcolor="rgba(0,0,0,0)", title=""), height=240)
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No zone data yet")

with chart2:
    st.markdown("<div class='section-header'>Violation Trend (Today)</div>", unsafe_allow_html=True)
    if stats and stats.get("hourly"):
        hourly_df = pd.DataFrame(stats["hourly"])
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=hourly_df["hour"], y=hourly_df["count"], fill="tozeroy",
                                  fillcolor="rgba(248,81,73,0.1)", line=dict(color="#f85149", width=2),
                                  mode="lines+markers", marker=dict(color="#f85149", size=5)))
        fig2.update_layout(plot_bgcolor="#161b22", paper_bgcolor="#161b22", font_color="#8b949e",
                           margin=dict(l=0, r=0, t=0, b=0),
                           xaxis=dict(gridcolor="#21262d", title=""),
                           yaxis=dict(gridcolor="#21262d", title=""), height=240, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("No hourly data yet")

# ─── Active alerts + incident log ──────────────────────────────────────────────
alert_col, log_col = st.columns([1, 2])

with alert_col:
    st.markdown("<div class='section-header'>Active Alerts</div>", unsafe_allow_html=True)
    unacked_list = [v for v in violations if not v.get("acknowledged")][:6]
    if not unacked_list:
        st.markdown("<div style='color:#3fb950;font-size:13px;padding:16px 0'>✓ No active violations</div>", unsafe_allow_html=True)
    for v in unacked_list:
        ts = datetime.fromisoformat(v["timestamp"])
        mins_ago = int((datetime.now() - ts).total_seconds() / 60)
        is_critical = "Hardhat" in v["violation"]
        badge = "badge-critical" if is_critical else "badge-warning"
        severity = "CRITICAL" if is_critical else "WARNING"
        border_color = "#f85149" if is_critical else "#d29922"
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #21262d;border-left:3px solid {border_color};border-radius:6px;padding:12px 14px;margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <span class="alert-badge {badge}">{severity}</span>
                <span style="font-size:11px;color:#8b949e">{mins_ago}m ago</span>
            </div>
            <div style="font-size:13px;font-weight:600;color:#e6edf3;margin-bottom:2px">{v['violation']}</div>
            <div style="font-size:12px;color:#8b949e">{v['zone']} · Conf: {v['confidence']:.0%}</div>
        </div>""", unsafe_allow_html=True)

with log_col:
    st.markdown("<div class='section-header'>Incident Log</div>", unsafe_allow_html=True)
    if violations:
        df = pd.DataFrame(violations)
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%H:%M:%S")
        df["confidence"] = df["confidence"].apply(lambda x: f"{x:.0%}")
        df["status"] = df["acknowledged"].apply(lambda x: "✓ Acked" if x else "⚠ Open")
        df["severity"] = df["violation"].apply(lambda x: "CRITICAL" if "Hardhat" in x else "WARNING")
        display_df = df[["timestamp", "zone", "violation", "confidence", "severity", "status"]]
        display_df.columns = ["Time", "Zone", "Violation", "Conf", "Severity", "Status"]
        st.dataframe(display_df, use_container_width=True, height=320, hide_index=True,
                     column_config={"Severity": st.column_config.TextColumn(width="small"),
                                    "Conf": st.column_config.TextColumn(width="small"),
                                    "Time": st.column_config.TextColumn(width="small")})
    else:
        st.info("No violations logged yet")

# ─── Zone risk overview ────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>Zone Risk Overview</div>", unsafe_allow_html=True)

all_zones = ["Entry Gate", "Scaffolding Area", "Material Yard", "Crane Zone", "Office Block"]
zone_data = {z["zone"]: z["count"] for z in stats.get("by_zone", [])} if stats else {}

zone_cols = st.columns(len(all_zones))
for i, zone in enumerate(all_zones):
    count = zone_data.get(zone, 0)
    risk  = "🔴 HIGH" if count > 20 else "🟡 MED" if count > 10 else "🟢 LOW"
    color = "#f85149" if count > 20 else "#d29922" if count > 10 else "#3fb950"
    with zone_cols[i]:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px;text-align:center">
            <div style="font-size:10px;color:#8b949e;margin-bottom:6px;font-weight:600">{zone.upper()}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:{color}">{count}</div>
            <div style="font-size:11px;color:{color};margin-top:4px">{risk}</div>
        </div>""", unsafe_allow_html=True)

# ─── Auto refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    rate_map = {"5s": 5, "10s": 10, "30s": 30}
    time.sleep(rate_map[refresh_rate])
    st.rerun()