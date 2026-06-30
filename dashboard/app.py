import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import requests
import time

# ─── Config ────────────────────────────────────────────────────────────────────
API_BASE = "http://localhost:8000"

st.set_page_config(
    page_title="SafeWatch — Construction Safety Monitor",
    page_icon="🦺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@600;700;800&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

    .stApp { background-color: #FAF7F4; color: #1C1917; }

    /* ── Top brand band, ONGC red, full width ── */
    .ongc-header {
        background: #7A1B26;
        margin: -1rem -4rem 28px -4rem;
        padding: 22px 4rem 20px 4rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 3px solid #1C1917;
    }
    .ongc-header .brand {
        font-family: 'Barlow Condensed', sans-serif;
        font-weight: 800;
        font-size: 28px;
        color: #FFFFFF;
        letter-spacing: 0.02em;
        text-transform: uppercase;
        line-height: 1;
    }
    .ongc-header .brand span { color: #E0B23D; }
    .ongc-header .sub {
        font-family: 'Inter', sans-serif;
        font-size: 11px;
        color: #E8C9C9;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        margin-top: 4px;
    }
    .ongc-header .status-block { text-align: right; }
    .ongc-header .live-row { color: #F2E0E0; font-size: 12px; font-family: 'JetBrains Mono', monospace; }

    /* ── Sidebar: neutral, lets header carry the brand ── */
    [data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 1px solid #E8DFD8; }
    [data-testid="stSidebar"] h3 { font-family: 'Barlow Condensed', sans-serif; font-weight: 800; font-size: 22px; color: #7A1B26 !important; letter-spacing: 0.02em; }
    [data-testid="stSidebar"] hr { border-color: #E8DFD8; }
    [data-testid="stSidebar"] label { color: #6B5F57 !important; font-weight: 600; font-size: 12px; text-transform: uppercase; letter-spacing: 0.04em; }
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background-color: #FAF7F4 !important; border: 1px solid #E8DFD8 !important; border-radius: 6px;
    }
    [data-testid="stSidebar"] caption, [data-testid="stSidebar"] .stCaption { color: #A89A8E !important; }

    /* ── Metric cards ── */
    .metric-card { background: #FFFFFF; border: 1px solid #E8DFD8; border-radius: 4px; padding: 20px 22px; position: relative; overflow: hidden; }
    .metric-card::before { content: ''; position: absolute; top: 0; left: 0; width: 5px; height: 100%; }
    .metric-card.danger::before  { background: #D93B3B; }
    .metric-card.warning::before { background: #E0B23D; }
    .metric-card.safe::before    { background: #2D8A4E; }
    .metric-card.brand::before   { background: #7A1B26; }

    .metric-label { font-size: 10px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; color: #A89A8E; margin-bottom: 10px; }
    .metric-value { font-family: 'Barlow Condensed', sans-serif; font-size: 42px; font-weight: 800; color: #1C1917; line-height: 1; }
    .metric-sub { font-size: 11px; color: #A89A8E; margin-top: 8px; font-family: 'Inter', sans-serif; }

    .alert-badge { display: inline-block; padding: 3px 10px; font-size: 10px; font-weight: 700; font-family: 'JetBrains Mono', monospace; letter-spacing: 0.04em; border-radius: 2px; }
    .badge-critical { background: #D93B3B; color: #FFFFFF; }
    .badge-warning  { background: #E0B23D; color: #1C1917; }
    .badge-safe     { background: #2D8A4E; color: #FFFFFF; }

    .section-header { font-family: 'Barlow Condensed', sans-serif; font-size: 16px; font-weight: 700; letter-spacing: 0.03em; text-transform: uppercase; color: #1C1917; border-bottom: 3px solid #7A1B26; padding-bottom: 8px; margin-bottom: 18px; display: inline-block; }

    .live-dot { display: inline-block; width: 8px; height: 8px; background: #E0B23D; border-radius: 50%; margin-right: 6px; animation: pulse 1.4s infinite; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }

    .zone-card { background: #FFFFFF; border: 1px solid #E8DFD8; border-top: 3px solid #7A1B26; border-radius: 4px; padding: 16px; text-align: center; }
    .empty-state { background: #FFFFFF; border: 1px dashed #D9CDC3; border-radius: 4px; padding: 32px; text-align: center; color: #A89A8E; font-size: 13px; }
    .violation-card { background: #FFFFFF; border: 1px solid #E8DFD8; border-radius: 4px; padding: 12px 14px; margin-bottom: 8px; }

    #MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
    .block-container { padding-top: 1rem; padding-bottom: 3rem; max-width: 100%; }
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
    st.markdown("### SafeWatch")
    st.markdown("<div style='color:#A89A8E;font-size:11px;margin-bottom:24px;letter-spacing:0.04em;text-transform:uppercase'>ONGC Site Safety Console</div>", unsafe_allow_html=True)
    st.markdown("**Filters**")
    zones = fetch_zones()
    selected_zone = st.selectbox("Zone", zones)
    selected_type = st.selectbox("Violation Type", ["All", "No Hardhat", "No Safety Vest"])
    limit = st.slider("Max Records", 10, 200, 30)
    st.markdown("---")
    st.markdown("**Auto-refresh**")
    auto_refresh = st.toggle("Enable", value=True)
    refresh_rate = st.selectbox("Interval", ["5s", "10s", "30s", "60s"])
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

# ─── Header band ───────────────────────────────────────────────────────────────
if not api_online:
    status_label, status_color = "API OFFLINE", "#E0B23D"
elif stats and stats.get("unacknowledged", 0) > 0:
    status_label, status_color = "VIOLATIONS DETECTED", "#FFFFFF"
else:
    status_label, status_color = "ALL CLEAR", "#FFFFFF"

st.markdown(f"""
<div class="ongc-header">
    <div>
        <div class="brand">Safe<span>Watch</span></div>
        <div class="sub">Construction Site Safety Monitor — ONGC</div>
    </div>
    <div class="status-block">
        <div style="color:{status_color};font-weight:700;font-size:13px;letter-spacing:0.06em;font-family:'JetBrains Mono',monospace">
            <span class="live-dot"></span>{status_label}
        </div>
        <div class="live-row">{datetime.now().strftime('%d %b %Y, %H:%M:%S')}</div>
    </div>
</div>
""", unsafe_allow_html=True)

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
    st.markdown(f'<div class="metric-card brand"><div class="metric-label">Today\'s Incidents</div><div class="metric-value">{today_count}</div><div class="metric-sub">Since midnight</div></div>', unsafe_allow_html=True)
with m3:
    st.markdown(f'<div class="metric-card warning"><div class="metric-label">No Hardhat</div><div class="metric-value">{no_hardhat}</div><div class="metric-sub">Helmet violations</div></div>', unsafe_allow_html=True)
with m4:
    st.markdown(f'<div class="metric-card warning"><div class="metric-label">No Safety Vest</div><div class="metric-value">{no_vest}</div><div class="metric-sub">Vest violations</div></div>', unsafe_allow_html=True)

st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

# ─── Charts ────────────────────────────────────────────────────────────────────
chart1, chart2 = st.columns(2)

with chart1:
    st.markdown("<div class='section-header'>Violations by Zone</div>", unsafe_allow_html=True)
    if stats and stats.get("by_zone"):
        zone_df = pd.DataFrame(stats["by_zone"])
        fig = px.bar(zone_df.sort_values("count", ascending=True), x="count", y="zone", orientation="h",
                     color="count", color_continuous_scale=["#E8C2C2", "#C25555", "#7A1B26"])
        fig.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", font_color="#6B5F57",
                          showlegend=False, coloraxis_showscale=False,
                          margin=dict(l=0, r=0, t=12, b=0),
                          xaxis=dict(gridcolor="#F0E8E2", title=""),
                          yaxis=dict(gridcolor="rgba(0,0,0,0)", title=""), height=240)
        fig.update_traces(marker_line_width=0)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div class="empty-state">No zone data yet</div>', unsafe_allow_html=True)

with chart2:
    st.markdown("<div class='section-header'>Violation Trend (Today)</div>", unsafe_allow_html=True)
    if stats and stats.get("hourly"):
        hourly_df = pd.DataFrame(stats["hourly"])
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=hourly_df["hour"], y=hourly_df["count"], fill="tozeroy",
                                  fillcolor="rgba(122,27,38,0.07)", line=dict(color="#7A1B26", width=2),
                                  mode="lines+markers", marker=dict(color="#7A1B26", size=5)))
        fig2.update_layout(plot_bgcolor="#FFFFFF", paper_bgcolor="#FFFFFF", font_color="#6B5F57",
                           margin=dict(l=0, r=0, t=12, b=0),
                           xaxis=dict(gridcolor="#F0E8E2", title=""),
                           yaxis=dict(gridcolor="#F0E8E2", title=""), height=240, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
    else:
        st.markdown('<div class="empty-state">No hourly data yet</div>', unsafe_allow_html=True)

st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

# ─── Active alerts + incident log ──────────────────────────────────────────────
alert_col, log_col = st.columns([1, 2])

with alert_col:
    st.markdown("<div class='section-header'>Active Alerts</div>", unsafe_allow_html=True)
    unacked_list = [v for v in violations if not v.get("acknowledged")][:6]
    if not unacked_list:
        st.markdown("<div style='color:#2D8A4E;font-size:13px;padding:16px 0;font-weight:600'>✓ No active violations</div>", unsafe_allow_html=True)
    for v in unacked_list:
        ts = datetime.fromisoformat(v["timestamp"])
        mins_ago = int((datetime.now() - ts).total_seconds() / 60)
        is_critical = "Hardhat" in v["violation"]
        badge = "badge-critical" if is_critical else "badge-warning"
        severity = "CRITICAL" if is_critical else "WARNING"
        border_color = "#D93B3B" if is_critical else "#E0B23D"
        st.markdown(f"""
        <div class="violation-card" style="border-left:4px solid {border_color}">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <span class="alert-badge {badge}">{severity}</span>
                <span style="font-size:11px;color:#A89A8E">{mins_ago}m ago</span>
            </div>
            <div style="font-size:13px;font-weight:600;color:#1C1917;margin-bottom:2px">{v['violation']}</div>
            <div style="font-size:12px;color:#6B5F57">{v['zone']} · Conf: {v['confidence']:.0%}</div>
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
        st.markdown('<div class="empty-state">No violations logged yet</div>', unsafe_allow_html=True)

# ─── Zone risk overview ────────────────────────────────────────────────────────
st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>Zone Risk Overview</div>", unsafe_allow_html=True)

all_zones = ["Entry Gate", "Scaffolding Area", "Material Yard", "Crane Zone", "Office Block"]
zone_data = {z["zone"]: z["count"] for z in stats.get("by_zone", [])} if stats else {}

zone_cols = st.columns(len(all_zones))
for i, zone in enumerate(all_zones):
    count = zone_data.get(zone, 0)
    risk  = "HIGH" if count > 20 else "MED" if count > 10 else "LOW"
    color = "#D93B3B" if count > 20 else "#E0B23D" if count > 10 else "#2D8A4E"
    with zone_cols[i]:
        st.markdown(f"""
        <div class="zone-card">
            <div style="font-size:10px;color:#A89A8E;margin-bottom:8px;font-weight:700;letter-spacing:0.06em">{zone.upper()}</div>
            <div style="font-family:'Barlow Condensed',sans-serif;font-size:30px;font-weight:800;color:{color}">{count}</div>
            <div style="font-size:10px;color:{color};margin-top:4px;font-weight:700;letter-spacing:0.06em">{risk}</div>
        </div>""", unsafe_allow_html=True)

# ─── Auto refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    rate_map = {"5s": 5, "10s": 10, "30s": 30, "60s": 60}
    time.sleep(rate_map[refresh_rate])
    st.rerun()