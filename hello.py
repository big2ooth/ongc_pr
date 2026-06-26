import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import time

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

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background-color: #0d1117;
        color: #e6edf3;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22;
        border-right: 1px solid #21262d;
    }

    /* Metric cards */
    .metric-card {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 8px;
        padding: 20px 24px;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0;
        width: 3px; height: 100%;
    }
    .metric-card.danger::before  { background: #f85149; }
    .metric-card.warning::before { background: #d29922; }
    .metric-card.safe::before    { background: #3fb950; }
    .metric-card.info::before    { background: #388bfd; }

    .metric-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #8b949e;
        margin-bottom: 8px;
    }
    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 32px;
        font-weight: 600;
        color: #e6edf3;
        line-height: 1;
    }
    .metric-sub {
        font-size: 12px;
        color: #8b949e;
        margin-top: 6px;
    }

    /* Alert badge */
    .alert-badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        font-family: 'JetBrains Mono', monospace;
    }
    .badge-critical { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
    .badge-warning  { background: rgba(210,153,34,0.15); color: #d29922; border: 1px solid rgba(210,153,34,0.3); }
    .badge-safe     { background: rgba(63,185,80,0.15);  color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }

    /* Section headers */
    .section-header {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #8b949e;
        border-bottom: 1px solid #21262d;
        padding-bottom: 8px;
        margin-bottom: 16px;
    }

    /* Violation row */
    .violation-row {
        background: #161b22;
        border: 1px solid #21262d;
        border-radius: 6px;
        padding: 12px 16px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 12px;
    }
    .violation-row.new {
        border-left: 3px solid #f85149;
        animation: pulse 2s infinite;
    }

    /* Live indicator */
    .live-dot {
        display: inline-block;
        width: 8px; height: 8px;
        background: #f85149;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 1.5s infinite;
    }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }

    /* Hide streamlit chrome */
    #MainMenu, footer, header { visibility: hidden; }
    .block-container { padding-top: 1.5rem; }

    /* Plotly charts dark */
    .js-plotly-plot { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ─── Dummy data ────────────────────────────────────────────────────────────────
ZONES = ["Entry Gate", "Scaffolding Area", "Material Yard", "Crane Zone", "Office Block"]
VIOLATION_TYPES = ["No Hardhat", "No Safety Vest", "No Hardhat + No Vest"]
SEVERITIES = ["CRITICAL", "CRITICAL", "WARNING"]

@st.cache_data(ttl=5)
def get_violations():
    now = datetime.now()
    rows = []
    for i in range(40):
        vtype = random.choice(VIOLATION_TYPES)
        rows.append({
            "id": f"V{1000+i}",
            "timestamp": now - timedelta(minutes=random.randint(0, 480)),
            "zone": random.choice(ZONES),
            "violation": vtype,
            "confidence": round(random.uniform(0.72, 0.97), 2),
            "severity": "CRITICAL" if "No Hardhat" in vtype else "WARNING",
            "acknowledged": random.choice([True, True, False])
        })
    return pd.DataFrame(rows).sort_values("timestamp", ascending=False)

def get_zone_counts(df):
    return df.groupby("zone").size().reset_index(name="violations")

def get_hourly(df):
    df = df.copy()
    df["hour"] = df["timestamp"].dt.floor("h")
    return df.groupby("hour").size().reset_index(name="count")

# ─── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🦺 SafeWatch")
    st.markdown("<div style='color:#8b949e;font-size:12px;margin-bottom:24px'>Construction Safety Monitor</div>", unsafe_allow_html=True)

    st.markdown("**Live Feed Source**")
    source = st.selectbox("", ["demo_video.mp4", "Webcam", "RTSP Stream"], label_visibility="collapsed")

    st.markdown("---")
    st.markdown("**Zone Filter**")
    selected_zones = st.multiselect("", ZONES, default=ZONES, label_visibility="collapsed")

    st.markdown("**Violation Type**")
    selected_types = st.multiselect("", VIOLATION_TYPES, default=VIOLATION_TYPES, label_visibility="collapsed")

    st.markdown("**Confidence Threshold**")
    conf_thresh = st.slider("", 0.0, 1.0, 0.4, 0.05, label_visibility="collapsed")

    st.markdown("---")
    st.markdown("**Auto-refresh**")
    auto_refresh = st.toggle("Enable", value=True)
    refresh_rate = st.selectbox("Interval", ["5s", "10s", "30s"], index=0)

    st.markdown("---")
    st.caption(f"Model: YOLOv8n  |  Classes: 5")
    st.caption(f"Source: {source}")

# ─── Main layout ───────────────────────────────────────────────────────────────
df = get_violations()
df_filtered = df[df["zone"].isin(selected_zones) & df["violation"].isin(selected_types)]
df_unacked = df_filtered[~df_filtered["acknowledged"]]

# Header
col_title, col_status = st.columns([3, 1])
with col_title:
    st.markdown("## Construction Site Safety Monitor")
    st.markdown(f"<span class='live-dot'></span><span style='color:#8b949e;font-size:13px'>LIVE — {datetime.now().strftime('%d %b %Y, %H:%M:%S')}</span>", unsafe_allow_html=True)
with col_status:
    status_color = "#f85149" if len(df_unacked) > 0 else "#3fb950"
    status_text = "VIOLATIONS DETECTED" if len(df_unacked) > 0 else "ALL CLEAR"
    st.markdown(f"<div style='text-align:right;margin-top:16px'><span class='alert-badge {'badge-critical' if len(df_unacked) > 0 else 'badge-safe'}'>{status_text}</span></div>", unsafe_allow_html=True)

st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

# ─── Metric cards ──────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)

with m1:
    st.markdown(f"""
    <div class="metric-card danger">
        <div class="metric-label">Active Violations</div>
        <div class="metric-value">{len(df_unacked)}</div>
        <div class="metric-sub">Unacknowledged alerts</div>
    </div>""", unsafe_allow_html=True)

with m2:
    today = df_filtered[df_filtered["timestamp"].dt.date == datetime.now().date()]
    st.markdown(f"""
    <div class="metric-card warning">
        <div class="metric-label">Today's Incidents</div>
        <div class="metric-value">{len(today)}</div>
        <div class="metric-sub">Last 8 hours</div>
    </div>""", unsafe_allow_html=True)

with m3:
    no_helmet = len(df_filtered[df_filtered["violation"].str.contains("Hardhat")])
    st.markdown(f"""
    <div class="metric-card danger">
        <div class="metric-label">No Hardhat</div>
        <div class="metric-value">{no_helmet}</div>
        <div class="metric-sub">Helmet violations</div>
    </div>""", unsafe_allow_html=True)

with m4:
    no_vest = len(df_filtered[df_filtered["violation"].str.contains("Vest")])
    st.markdown(f"""
    <div class="metric-card warning">
        <div class="metric-label">No Safety Vest</div>
        <div class="metric-value">{no_vest}</div>
        <div class="metric-sub">Vest violations</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

# ─── Charts row ────────────────────────────────────────────────────────────────
chart1, chart2 = st.columns([1, 1])

with chart1:
    st.markdown("<div class='section-header'>Violations by Zone</div>", unsafe_allow_html=True)
    zone_df = get_zone_counts(df_filtered)
    fig = px.bar(
        zone_df.sort_values("violations", ascending=True),
        x="violations", y="zone", orientation="h",
        color="violations",
        color_continuous_scale=["#388bfd", "#d29922", "#f85149"],
    )
    fig.update_layout(
        plot_bgcolor="#161b22", paper_bgcolor="#161b22",
        font_color="#8b949e", font_family="Inter",
        showlegend=False, coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(gridcolor="#21262d", title=""),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", title=""),
        height=240
    )
    fig.update_traces(marker_line_width=0)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

with chart2:
    st.markdown("<div class='section-header'>Violation Trend (Last 8 hrs)</div>", unsafe_allow_html=True)
    hourly = get_hourly(df_filtered)
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=hourly["hour"], y=hourly["count"],
        fill="tozeroy",
        fillcolor="rgba(248,81,73,0.1)",
        line=dict(color="#f85149", width=2),
        mode="lines"
    ))
    fig2.update_layout(
        plot_bgcolor="#161b22", paper_bgcolor="#161b22",
        font_color="#8b949e", font_family="Inter",
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(gridcolor="#21262d", title=""),
        yaxis=dict(gridcolor="#21262d", title=""),
        height=240, showlegend=False
    )
    st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})

# ─── Live alerts + incident log ────────────────────────────────────────────────
alert_col, log_col = st.columns([1, 2])

with alert_col:
    st.markdown("<div class='section-header'>Active Alerts</div>", unsafe_allow_html=True)
    recent = df_unacked.head(6)
    if len(recent) == 0:
        st.markdown("<div style='color:#3fb950;font-size:13px;padding:16px 0'>✓ No active violations</div>", unsafe_allow_html=True)
    for _, row in recent.iterrows():
        badge = "badge-critical" if row["severity"] == "CRITICAL" else "badge-warning"
        mins_ago = int((datetime.now() - row["timestamp"]).total_seconds() / 60)
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #21262d;border-left:3px solid {'#f85149' if row['severity']=='CRITICAL' else '#d29922'};
        border-radius:6px;padding:12px 14px;margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">
                <span class="alert-badge {badge}">{row['severity']}</span>
                <span style="font-size:11px;color:#8b949e">{mins_ago}m ago</span>
            </div>
            <div style="font-size:13px;font-weight:600;color:#e6edf3;margin-bottom:2px">{row['violation']}</div>
            <div style="font-size:12px;color:#8b949e">{row['zone']}</div>
        </div>
        """, unsafe_allow_html=True)

with log_col:
    st.markdown("<div class='section-header'>Incident Log</div>", unsafe_allow_html=True)
    display_df = df_filtered.head(15).copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%H:%M:%S")
    display_df["confidence"] = display_df["confidence"].apply(lambda x: f"{x:.0%}")
    display_df["status"] = display_df["acknowledged"].apply(lambda x: "✓ Acked" if x else "⚠ Open")
    display_df = display_df[["timestamp", "zone", "violation", "confidence", "severity", "status"]]
    display_df.columns = ["Time", "Zone", "Violation", "Conf", "Severity", "Status"]

    st.dataframe(
        display_df,
        use_container_width=True,
        height=320,
        hide_index=True,
        column_config={
            "Severity": st.column_config.TextColumn(width="small"),
            "Conf": st.column_config.TextColumn(width="small"),
            "Time": st.column_config.TextColumn(width="small"),
        }
    )

# ─── Zone risk heatmap ─────────────────────────────────────────────────────────
st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
st.markdown("<div class='section-header'>Zone Risk Overview</div>", unsafe_allow_html=True)

zone_cols = st.columns(len(ZONES))
for i, zone in enumerate(ZONES):
    zone_violations = len(df_filtered[df_filtered["zone"] == zone])
    risk = "🔴 HIGH" if zone_violations > 10 else "🟡 MED" if zone_violations > 5 else "🟢 LOW"
    risk_color = "#f85149" if zone_violations > 10 else "#d29922" if zone_violations > 5 else "#3fb950"
    with zone_cols[i]:
        st.markdown(f"""
        <div style="background:#161b22;border:1px solid #21262d;border-radius:8px;padding:14px;text-align:center">
            <div style="font-size:11px;color:#8b949e;margin-bottom:6px;font-weight:600">{zone.upper()}</div>
            <div style="font-family:'JetBrains Mono',monospace;font-size:24px;font-weight:700;color:{risk_color}">{zone_violations}</div>
            <div style="font-size:11px;color:{risk_color};margin-top:4px">{risk}</div>
        </div>
        """, unsafe_allow_html=True)

# ─── Auto refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    rate_map = {"5s": 5, "10s": 10, "30s": 30}
    time.sleep(rate_map[refresh_rate])
    st.rerun()