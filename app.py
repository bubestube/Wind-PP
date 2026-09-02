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

WIND_COLORSCALE_GUST = [
    [0.00, "rgba(255, 255, 255, 0.25)"],
    [0.22, "rgba(56, 189, 248, 0.30)"],
    [0.40, "rgba(37, 99, 235, 0.35)"],
    [0.55, "rgba(34, 197, 94, 0.40)"],
    [0.70, "rgba(234, 179, 8, 0.45)"],
    [0.85, "rgba(168, 85, 247, 0.50)"],
    [1.00, "rgba(239, 68, 68, 0.55)"]
]

WIND_COLORSCALE_SPEED = [
    [0.00, "rgba(255, 255, 255, 0.50)"],
    [0.22, "rgba(56, 189, 248, 0.55)"],
    [0.40, "rgba(37, 99, 235, 0.60)"],
    [0.55, "rgba(34, 197, 94, 0.65)"],
    [0.70, "rgba(234, 179, 8, 0.70)"],
    [0.85, "rgba(168, 85, 247, 0.75)"],
    [1.00, "rgba(239, 68, 68, 0.80)"]
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
    /* Mobile Touch Layer Stabilization */
    div[data-testid="stPlotlyChart"] {
        touch-action: pan-y !important;
        -webkit-user-select: none !important;
        user-select: none !important;
    }
    div[data-testid="stPlotlyChart"] .main-svg {
        touch-action: pan-y !important;
    }
    /* Enlarged touch targets for Streamlit buttons */
    div.stButton > button {
        min-height: 42px;
        font-size: 15px;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🪁 Porto Pollo (Sardinia) – Live Wind Station")

# 1. Fast Cached CSV Loader
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

    # 2. Status KPI Cards
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

    # 3. Dynamic Timeline Navigation & Touch Zoom Controls
    if "window_end_time" not in st.session_state:
        st.session_state.window_end_time = t_global_max.to_pydatetime()
    if "window_span_hours" not in st.session_state:
        st.session_state.window_span_hours = 6

    # Touch-Optimized Control Bar
    st.markdown("**📱 Mobile Zoom & Navigation**")
    tb1, tb2, tb3, tb4, tb5, tb6 = st.columns([1, 1, 1, 1, 1.2, 1.2])

    with tb1:
        if st.button("🔍 In (+)", help="Zoom in (Halve time range)"):
            st.session_state.window_span_hours = max(2, int(st.session_state.window_span_hours * 0.6))
            st.rerun()
    with tb2:
        if st.button("🔍 Out (-)", help="Zoom out (Expand time range)"):
            st.session_state.window_span_hours = min(168, int(st.session_state.window_span_hours * 1.6))
            st.rerun()
    with tb3:
        if st.button("◀ Back"):
            step = max(2, int(st.session_state.window_span_hours * 0.5))
            st.session_state.window_end_time = max(
                (t_global_min + pd.Timedelta(hours=st.session_state.window_span_hours)).to_pydatetime(),
                st.session_state.window_end_time - datetime.timedelta(hours=step)
            )
            st.rerun()
    with tb4:
        if st.button("Forward ▶"):
            step = max(2, int(st.session_state.window_span_hours * 0.5))
            st.session_state.window_end_time = min(
                t_global_max.to_pydatetime(),
                st.session_state.window_end_time + datetime.timedelta(hours=step)
            )
            st.rerun()
    with tb5:
        if st.button("🔴 Reset/Live"):
            st.session_state.window_end_time = t_global_max.to_pydatetime()
            st.session_state.window_span_hours = 6
            st.rerun()
    with tb6:
        daytime_only = st.checkbox("☀️ 06-19h", value=False)

    # Timeline Scrubber Slider
    min_slider = (t_global_min + pd.Timedelta(hours=st.session_state.window_span_hours)).to_pydatetime()
    max_slider = t_global_max.to_pydatetime()

    if min_slider < max_slider:
        selected_end = st.slider(
            "Timeline Scrubber:",
            min_value=min_slider,
            max_value=max_slider,
            value=st.session_state.window_end_time,
            format="DD.MM HH:mm",
            step=datetime.timedelta(minutes=15)
        )
        st.session_state.window_end_time = selected_end

    v_end = pd.to_datetime(st.session_state.window_end_time)
    v_start = v_end - pd.Timedelta(hours=st.session_state.window_span_hours)

    # 4. Slice Data for Active Window
    df_slice = df_all[(df_all["timestamp"] >= v_start) & (df_all["timestamp"] <= v_end)].copy()

    if daytime_only:
        df_slice = df_slice[df_slice["timestamp"].dt.hour.between(6, 18)].copy()

    if df_slice.empty:
        st.warning("No records in selected window.")
        df_slice = df_all.tail(20).copy()

    df_slice["velocita_bft"] = knots_to_bft(df_slice["velocita_knots"])
    df_slice["raffica_bft"] = knots_to_bft(df_slice["raffica_knots"])
    df_slice["velocita_plot_y"] = bft_to_stretched(df_slice["velocita_bft"])
    df_slice["raffica_plot_y"] = bft_to_stretched(df_slice["raffica_bft"])
    df_slice["arrow_angle"] = (df_slice["direzione_deg"].fillna(0) + 180) % 360

    has_temp = "temperatura_c" in df_slice.columns and df_slice["temperatura_c"].notnull().any()

    # Gap Disconnectors
    df_plot = df_slice.sort_values("timestamp").reset_index(drop=True)
    time_diffs = df_plot["timestamp"].diff()
    gap_indices = df_plot[time_diffs > pd.Timedelta(minutes=45)].index

    if len(gap_indices) > 0:
        nan_rows = []
        for idx in gap_indices:
            prev_time = df_plot.loc[idx - 1, "timestamp"]
            nan_rows.append(pd.DataFrame(
