import datetime
import math
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="Porto Pollo – Windguru Live Station",
    page_icon="🪁",
    layout="wide"
)

CSV_FILE = "porto_pollo_wind_history.csv"
BFT_EXP = 1.55

# --- Vectorized Calculations ---
def knots_to_bft(knots):
    if isinstance(knots, pd.Series):
        s = pd.to_numeric(knots, errors="coerce").clip(lower=0)
        return np.power(s / 1.625, 2.0 / 3.0)
    if pd.isna(knots):
        return np.nan
    return np.power(max(0.0, float(knots)) / 1.625, 2.0 / 3.0)

def bft_to_stretched(bft_val):
    if isinstance(bft_val, pd.Series):
        s = pd.to_numeric(bft_val, errors="coerce").clip(lower=0)
        return np.power(s, BFT_EXP)
    if pd.isna(bft_val):
        return np.nan
    return math.pow(max(0.0, float(bft_val)), BFT_EXP)

def deg_to_cardinal(deg):
    if pd.isna(deg):
        return ""
    dirs = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
            "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
    ix = int(round(deg / (360.0 / len(dirs)))) % len(dirs)
    return dirs[ix]

WIND_COLORSCALE_SMOOTH = [
    [0.00, "#ffffff"],
    [0.12, "#e0f2fe"],
    [0.25, "#7dd3fc"],
    [0.40, "#38bdf8"],
    [0.55, "#4ade80"],
    [0.70, "#facc15"],
    [0.85, "#c084fc"],
    [1.00, "#f87171"]
]

def get_wg_badge(val):
    if pd.isna(val):
        return "#94a3b8", "#ffffff"
    if val < 7:
        return "#f1f5f9", "#0f172a"
    elif val < 14:
        return "#38bdf8", "#0f172a"
    elif val < 20:
        return "#4ade80", "#0f172a"
    elif val < 27:
        return "#facc15", "#0f172a"
    elif val < 35:
        return "#c084fc", "#ffffff"
    else:
        return "#f87171", "#ffffff"

st.markdown("""
    <style>
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    .wg-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        text-align: center;
    }
    .wg-card-title {
        font-size: 0.8rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748b;
        margin-bottom: 4px;
    }
    .wg-card-val {
        font-size: 1.6rem;
        font-weight: 700;
        font-family: monospace;
    }
    div.stButton > button {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
    }
    div.stButton > button:hover {
        background-color: #f8fafc !important;
        border-color: #94a3b8 !important;
        color: #0284c7 !important;
    }
    .scroll-hint {
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 0.85rem;
        color: #475569;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🪁 Porto Pollo (Sardinia) – Live Wind Station")

@st.cache_data(ttl=60, show_spinner=False)
def load_all_records(csv_path):
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path, on_bad_lines="skip")
        if df.empty or "timestamp" not in df.columns:
            return None
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        df = df[df["timestamp"] >= "2026-08-27 13:11:00"].reset_index(drop=True)
        return df if not df.empty else None
    except Exception:
        return None

df_all = load_all_records(CSV_FILE)

if df_all is not None and not df_all.empty:
    latest = df_all.iloc[-1]
    latest_bft = knots_to_bft(latest['velocita_knots'])
    t_global_max = df_all["timestamp"].max()
    t_global_min = df_all["timestamp"].min()

    # KPI Top Cards
    speed_bg, speed_fg = get_wg_badge(latest['velocita_knots'])
    gust_bg, gust_fg = get_wg_badge(latest['raffica_knots'])
    temp_val = latest.get("temperatura_c")

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">💨 Live Wind (Bft / Knots)</div>
            <div class="wg-card-val" style="color: {speed_fg}; background:{speed_bg}; border-radius:4px; padding:2px;">
                {latest_bft:.1f} <span style="font-size:0.9rem;">Bft</span> <span style="font-size:0.85rem; font-weight:normal;">({latest['velocita_knots']:.1f} kts)</span>
            </div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">💨 Live Gust (Knots)</div>
            <div class="wg-card-val" style="color: {gust_fg}; background:{gust_bg}; border-radius:4px; padding:2px;">
                {latest['raffica_knots']:.1f} <span style="font-size:0.9rem;">kts</span>
            </div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">🧭 Direction</div>
            <div class="wg-card-val" style="color: #0f172a;">
                {latest['direzione_cardinal']} <span style="font-size:1.1rem; color:#64748b;">({latest['direzione_deg']:.0f}°)</span>
            </div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">🌡️ Temperature</div>
            <div class="wg-card-val" style="color: #ca8a04;">
                {f"{temp_val:.1f} °C" if pd.notnull(temp_val) else "N/A"}
            </div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">⏱️ Last Reading</div>
            <div class="wg-card-val" style="font-size:1.1rem; padding-top:6px; color:#334155;">
                {latest['timestamp'].strftime('%d.%m. %H:%M')}
            </div>
        </div>""", unsafe_allow_html=True)

    st.write("")

    # Interactive Navigation Hint & Quick Jump Toolbar
    bar_col1, bar_col2 = st.columns([4, 1])
    with bar_col1:
        st.markdown(
            '<div class="scroll-hint">🖱️ <b>Infinite Canvas:</b> Drag horizontally to pan backwards in time. Scroll / pinch to zoom. Use the minimap slider below for global scrubbing.</div>',
            unsafe_allow_html=True
        )
    with bar_col2:
        if st.button("🔴 Reset to Live"):
            st.rerun()

    # Pre-process Continuous Dataset (10-minute uniform grid)
    df_chart = df_all.set_index("timestamp").resample("10min").agg({
        "velocita_knots": "mean",
        "raffica_knots": "max",
        "direzione_deg": "mean",
        "temperatura_c": "mean"
    }).interpolate(method="time", limit=4).dropna(subset=["velocita_knots"]).reset_index()

    df_chart["direzione_cardinal"] = df_chart["direzione_deg"].apply(deg_to_cardinal)
    df_chart["velocita_bft"] = knots_to_bft(df_chart["velocita_knots"])
    df_chart["raffica_bft"] = knots_to_bft(df_chart["raffica_knots"])
    df_chart["velocita_plot_y"] = bft_to_stretched(df_chart["velocita_bft"])
    df_chart["raffica_plot_y"] = bft_to_stretched(df_chart["raffica_bft"])
    # Plotly's symbol="arrow-up" points North (0°). Rotating by arrow_angle points to wind direction:
    df_chart["arrow_angle"] = (df_chart["direzione_deg"].fillna(0) + 180) % 360

    # Dynamic Cadence for Windspeed Text Labels & Direction Arrow Glyphs
    # Step every 3rd point (every 30 mins) to maintain clean readability
    speed_labels = []
    gust_labels = []
    for i, row in df_chart.iterrows():
        if i % 3 == 0:
            speed_labels.append(f"{row['velocita_knots']:.1f}")
            gust_labels.append(f"{row['raffica_knots']:.1f}")
        else:
            speed_labels.append("")
            gust_labels.append("")
    df_chart["speed_label"] = speed_labels
    df_chart["gust_label"] = gust_labels

    has_temp = "temperatura_c" in df_chart.columns and df_chart["temperatura_c"].notnull().any()
    max_observed_y = df_chart["raffica_plot_y"].dropna().max() if not df_chart["raffica_plot_y"].dropna().empty else bft_to_stretched(7.5)
    top_y_limit = max(bft_to_stretched(7.5), max_observed_y * 1.15)

    # Initial default view: Last 24 Hours
    default_start = t_global_max - pd.Timedelta(hours=24)
    default_end = t_global_max

    fig = make_subplots(
        rows=3 if has_temp else 2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        subplot_titles=(
            "<b>Wind speed and gusts (Stretched Beaufort Scale) – Pan & Zoom Enabled</b>",
            "<b>Wind direction & Vectors</b>",
            "<b>Temperature (°C)</b>" if has_temp else None
        ),
        row_heights=[0.54, 0.28, 0.18] if has_temp else [0.65, 0.35]
    )

    # 1. Continuous Background Gradient Heatmap
    y_levels = np.linspace(0, top_y_limit, 45)
    bft_levels = np.power(y_levels, 1.0 / BFT_EXP)
    z_gradient = np.tile(bft_levels, (2, 1)).T

    fig.add_trace(go.Heatmap(
        x=[t_global_min, t_global_max],
        y=y_levels,
        z=z_gradient,
        colorscale=WIND_COLORSCALE_SMOOTH,
        zmin=0,
        zmax=8,
        showscale=False,
        hoverinfo="skip"
    ), row=1, col=1)

    # 2. Inverted White Ceiling Mask
    x_mask = [t_global_min] + list(df_chart["timestamp"]) + [t_global_max, t_global_max, t_global_min]
    y_mask = [df_chart["raffica_plot_y"].iloc[0]] + list(df_chart["raffica_plot_y"]) + [
        df_chart["raffica_plot_y"].iloc[-1], top_y_limit * 1.10, top_y_limit * 1.10
    ]

    fig.add_trace(go.Scatter(
        x=x_mask,
        y=y_mask,
        fill="toself",
        fillcolor="#ffffff",
        line=dict(color="rgba(255, 255, 255, 0)", width=0),
        hoverinfo="skip",
        showlegend=False
    ), row=1, col=1)

    # 3. Gust Trace (Lines + Markers + Labels Above)
    fig.add_trace(go.Scatter(
        x=df_chart["timestamp"],
        y=df_chart["raffica_plot_y"],
        text=df_chart["gust_label"],
        textposition="top center",
        textfont=dict(family="Arial, sans-serif", size=10, color="#b91c1c"),
        customdata=np.stack((df_chart["raffica_bft"], df_chart["raffica_knots"]), axis=-1),
        mode="lines+markers+text",
        name="Gust (Raffica)",
        line=dict(color="#0f172a", width=1.5, dash="dot"),
        marker=dict(symbol="circle", size=3.5, color="#0f172a"),
        hovertemplate="<b>Gust:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=1, col=1)

    # 4. Sustained Speed Trace (Lines + Arrow Glyphs + Knots Labels Underneath)
    fig.add_trace(go.Scatter(
        x=df_chart["timestamp"],
        y=df_chart["velocita_plot_y"],
        text=df_chart["speed_label"],
        textposition="bottom center",
        textfont=dict(family="Arial, sans-serif", size=10, color="#0f172a"),
        customdata=np.stack((df_chart["velocita_bft"], df_chart["velocita_knots"], df_chart["direzione_deg"]), axis=-1),
        mode="lines+markers+text",
        name="Wind Speed (Avg)",
        line=dict(color="#0f172a", width=2.0),
        marker=dict(
            symbol="arrow-up",
            size=10,
            angle=df_chart["arrow_angle"],
            color="#0f172a"
        ),
        hovertemplate="<b>Speed:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<br><b>Dir:</b> %{customdata[2]:.0f}°<extra></extra>"
    ), row=1, col=1)

    # 5. Direction Subplot (Arrow Vector Glyphs Colored by Force)
    # Green if >= 18 knots, Red/Grey otherwise
    arrow_colors = np.where(df_chart["velocita_knots"] >= 18.0, "#16a34a", "#dc2626")

    fig.add_trace(go.Scatter(
        x=df_chart["timestamp"],
        y=df_chart["direzione_deg"],
        mode="markers",
        name="Direction Arrow",
        marker=dict(
            symbol="arrow-up",
            size=13,
            angle=df_chart["arrow_angle"],
            color=arrow_colors
        ),
        customdata=df_chart[["direzione_cardinal", "velocita_knots", "velocita_bft"]],
        hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[2]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=2, col=1)

    # 6. Temperature Trace
    if has_temp:
        fig.add_trace(go.Scatter(
            x=df_chart["timestamp"],
            y=df_chart["temperatura_c"],
            mode="lines+markers",
            name="Temperature",
            marker=dict(size=3, color="#ca8a04"),
            line=dict(color="#eab308", width=1.8),
            hovertemplate="<b>Temp:</b> %{y:.1f} °C<extra></extra>"
        ), row=3, col=1)

    # Axis Formatting
    bft_ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    bft_stretched_vals = [bft_to_stretched(b) for b in bft_ticks]
    bft_labels = ["0 Bft", "1 Bft", "2 Bft", "3 Bft", "4 Bft", "5 Bft", "6 Bft", "7 Bft", "8 Bft", "9 Bft"]

    fig.update_yaxes(
        title_text="<b>Beaufort</b>",
        range=[0, top_y_limit],
        tickvals=bft_stretched_vals,
        ticktext=bft_labels,
        fixedrange=True,
        row=1, col=1
    )

    fig.update_yaxes(
        title_text="<b>Direction</b>",
        range=[-35, 395],
        tickvals=[0, 90, 180, 270, 360],
        ticktext=["N (0°)", "E (90°)", "S (180°)", "W (270°)", "N (360°)"],
        fixedrange=True,
        row=2, col=1
    )

    if has_temp:
        fig.update_yaxes(title_text="<b>°C</b>", fixedrange=True, row=3, col=1)

    # Setup Pan/Zoom Viewport + Rangeslider Minimap
    fig.update_xaxes(
        range=[default_start, default_end],
        rangeslider=dict(
            visible=True,
            thickness=0.06,
            bgcolor="#f8fafc"
        ),
        gridcolor="#cbd5e1",
        showgrid=True,
        row=3 if has_temp else 2, col=1
    )

    fig.update_layout(
        height=820 if has_temp else 650,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        dragmode="pan",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=35, r=20, t=50, b=30)
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"]
        }
    )

    with st.expander("📋 View Data Log (Active Window)"):
        st.dataframe(
            df_chart.sort_values("timestamp", ascending=False),
            use_container_width=True
        )
else:
    st.info("No data file found yet.")
