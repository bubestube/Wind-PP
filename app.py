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

WIND_COLORSCALE_GUST = [
    [0.00, "rgba(255, 255, 255, 0.25)"],
    [0.22, "rgba(56, 189, 248, 0.35)"],
    [0.40, "rgba(37, 99, 235, 0.45)"],
    [0.55, "rgba(34, 197, 94, 0.50)"],
    [0.70, "rgba(234, 179, 8, 0.55)"],
    [0.85, "rgba(168, 85, 247, 0.60)"],
    [1.00, "rgba(239, 68, 68, 0.65)"]
]

WIND_COLORSCALE_SPEED = [
    [0.00, "rgba(255, 255, 255, 0.50)"],
    [0.22, "rgba(56, 189, 248, 0.55)"],
    [0.40, "rgba(37, 99, 235, 0.65)"],
    [0.55, "rgba(34, 197, 94, 0.70)"],
    [0.70, "rgba(234, 179, 8, 0.75)"],
    [0.85, "rgba(168, 85, 247, 0.80)"],
    [1.00, "rgba(239, 68, 68, 0.85)"]
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
    div.stButton > button p, div.stButton > button span {
        color: inherit !important;
    }
    div[data-testid="stSelectbox"] label p {
        color: #475569 !important;
        font-weight: 600 !important;
    }
    div[data-testid="stSelectbox"] div[role="combobox"] {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        border-radius: 6px !important;
    }
    .slider-month-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.90rem;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 6px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
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

df_raw = load_all_records(CSV_FILE)

if df_raw is not None and not df_raw.empty:
    latest = df_raw.iloc[-1]
    latest_bft = knots_to_bft(latest['velocita_knots'])
    t_global_max = df_raw["timestamp"].max()
    t_global_min = df_raw["timestamp"].min()

    # Top KPI Cards
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

    # Viewport State Initialization
    if "window_end_time" not in st.session_state:
        st.session_state.window_end_time = t_global_max.to_pydatetime()
    if "window_span_hours" not in st.session_state:
        st.session_state.window_span_hours = 24

    if st.session_state.window_end_time > t_global_max.to_pydatetime():
        st.session_state.window_end_time = t_global_max.to_pydatetime()

    window_options = [6, 12, 24, 72, 168, 720]
    curr_span = st.session_state.get("window_span_hours", 24)
    curr_idx = window_options.index(curr_span) if curr_span in window_options else 2

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5, ctrl_col6 = st.columns([1, 1, 1.3, 1.2, 1, 1])
    with ctrl_col3:
        selected_span = st.selectbox(
            "Window Width:",
            options=window_options,
            index=curr_idx,
            format_func=lambda h: f"{h} Hours" if h < 24 else f"{h//24} Day{'s' if h > 24 else ''}"
        )
        if selected_span != st.session_state.window_span_hours:
            st.session_state.window_span_hours = selected_span
            st.rerun()

    span_h = st.session_state.window_span_hours

    # Density thresholds & slider resolution
    if span_h >= 720:          # 30 Days
        resample_rule = "2h"
        slider_freq = "2h"
    elif span_h >= 168:        # 7 Days
        resample_rule = "30min"
        slider_freq = "30min"
    elif span_h >= 72:         # 3 Days
        resample_rule = "20min"
        slider_freq = "20min"
    else:                      # <= 1 Day
        resample_rule = None
        slider_freq = "15min"

    min_allowable_end = (t_global_min + pd.Timedelta(hours=span_h)).to_pydatetime()
    max_allowable_end = t_global_max.to_pydatetime()

    with ctrl_col1:
        if st.button("◀ -1 Day"):
            st.session_state.window_end_time = max(
                min_allowable_end,
                st.session_state.window_end_time - datetime.timedelta(days=1)
            )
            st.rerun()
    with ctrl_col2:
        if st.button("◀ -6 Hours"):
            st.session_state.window_end_time = max(
                min_allowable_end,
                st.session_state.window_end_time - datetime.timedelta(hours=6)
            )
            st.rerun()
    with ctrl_col4:
        daytime_only = st.checkbox("☀️ Daytime Only (06-19h)", value=False)
    with ctrl_col5:
        if st.button("+6 Hours ▶"):
            st.session_state.window_end_time = min(
                max_allowable_end,
                st.session_state.window_end_time + datetime.timedelta(hours=6)
            )
            st.rerun()
    with ctrl_col6:
        if st.button("🔴 Live Latest"):
            st.session_state.window_end_time = max_allowable_end
            st.rerun()

    # Fixed end point bounded strictly to max data point
    v_end = min(pd.to_datetime(st.session_state.window_end_time), t_global_max)
    v_start = v_end - pd.Timedelta(hours=span_h)

    # Windguru Active Timeline Header
    date_display_str = f"{v_start.strftime('%a %d.%m. %H:%M')} ➔ {v_end.strftime('%a %d.%m. %H:%M')}"
    st.markdown(
        f'<div class="slider-month-pill">📅 <span><b>{date_display_str}</b></span> ({span_h}h window)</div>',
        unsafe_allow_html=True
    )

    # --- Windguru Date & Time Slider ---
    # Construct a complete sequence of dates and hours to scrub through
    timeline_ticks = pd.date_range(start=min_allowable_end, end=max_allowable_end, freq=slider_freq).to_pydatetime().tolist()
    if not timeline_ticks or timeline_ticks[-1] != max_allowable_end:
        timeline_ticks.append(max_allowable_end)

    # Find closest tick to current state
    curr_target = min(v_end.to_pydatetime(), max_allowable_end)
    closest_idx = int(np.argmin([abs((t - curr_target).total_seconds()) for t in timeline_ticks]))

    def format_windguru_slider(tick_dt):
        return tick_dt.strftime("%a %d.%m. %H:%M")

    selected_slider_idx = st.select_slider(
        "Timeline Scrubber (Day, Date & Time):",
        options=range(len(timeline_ticks)),
        value=closest_idx,
        format_func=lambda idx: format_windguru_slider(timeline_ticks[idx])
    )

    chosen_dt = timeline_ticks[selected_slider_idx]
    if abs((chosen_dt - v_end.to_pydatetime()).total_seconds()) > 60:
        st.session_state.window_end_time = chosen_dt
        st.rerun()

    # Slice only within data boundaries (Zero future overshoot)
    df_slice = df_raw[(df_raw["timestamp"] >= v_start) & (df_raw["timestamp"] <= v_end)].copy()

    if daytime_only:
        df_slice = df_slice[df_slice["timestamp"].dt.hour.between(6, 18)].copy()

    if df_slice.empty:
        df_slice = df_raw.tail(40).copy()

    if resample_rule is not None and not df_slice.empty:
        df_agg = df_slice.set_index("timestamp").resample(resample_rule).agg({
            "velocita_knots": "mean",
            "raffica_knots": "max",
            "direzione_deg": "mean",
            "temperatura_c": "mean"
        })
        df_resampled = df_agg.interpolate(method="time", limit=3).dropna(subset=["velocita_knots"]).reset_index()
        df_resampled["direzione_cardinal"] = df_resampled["direzione_deg"].apply(deg_to_cardinal)
        df_chart = df_resampled
    else:
        df_chart = df_slice.sort_values("timestamp").reset_index(drop=True)

    df_chart["velocita_bft"] = knots_to_bft(df_chart["velocita_knots"])
    df_chart["raffica_bft"] = knots_to_bft(df_chart["raffica_knots"])
    df_chart["velocita_plot_y"] = bft_to_stretched(df_chart["velocita_bft"])
    df_chart["raffica_plot_y"] = bft_to_stretched(df_chart["raffica_bft"])
    df_chart["arrow_angle"] = (df_chart["direzione_deg"].fillna(0) + 180) % 360

    has_temp = "temperatura_c" in df_chart.columns and df_chart["temperatura_c"].notnull().any()
    max_observed_y = df_chart["raffica_plot_y"].dropna().max() if not df_chart["raffica_plot_y"].dropna().empty else bft_to_stretched(7.5)
    top_y_limit = max(b
