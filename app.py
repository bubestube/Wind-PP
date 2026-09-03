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

# Continuous Beaufort Color Scale for Horizontal Area Fill
WIND_COLORSCALE_SMOOTH = [
    [0.00, "#ffffff"],  # 0 Bft
    [0.12, "#e0f2fe"],  # 1 Bft
    [0.25, "#7dd3fc"],  # 2-3 Bft
    [0.40, "#38bdf8"],  # 4 Bft
    [0.55, "#4ade80"],  # 5 Bft
    [0.70, "#facc15"],  # 6 Bft
    [0.85, "#c084fc"],  # 7 Bft
    [1.00, "#f87171"]   # 8+ Bft
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

    div[data-testid="stCheckbox"] {
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        padding: 5px 10px !important;
        margin-top: 25px !important;
    }
    div[data-testid="stCheckbox"] label p {
        color: #0f172a !important;
        font-weight: 600 !important;
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
        margin-bottom: 4px;
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

df_all = load_all_records(CSV_FILE)

if df_all is not None and not df_all.empty:
    latest = df_all.iloc[-1]
    latest_bft = knots_to_bft(latest['velocita_knots'])
    t_global_max = df_all["timestamp"].max()
    t_global_min = df_all["timestamp"].min()

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

    if "window_end_time" not in st.session_state:
        st.session_state.window_end_time = t_global_max.to_pydatetime()
    if "window_span_hours" not in st.session_state:
        st.session_state.window_span_hours = 24

    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4, ctrl_col5, ctrl_col6 = st.columns([1, 1, 1.3, 1.2, 1, 1])
    with ctrl_col1:
        if st.button("◀ -1 Day"):
            st.session_state.window_end_time = max(
                (t_global_min + pd.Timedelta(hours=st.session_state.window_span_hours)).to_pydatetime(),
                st.session_state.window_end_time - datetime.timedelta(days=1)
            )
            st.rerun()
    with ctrl_col2:
        if st.button("◀ -6 Hours"):
            st.session_state.window_end_time = max(
                (t_global_min + pd.Timedelta(hours=st.session_state.window_span_hours)).to_pydatetime(),
                st.session_state.window_end_time - datetime.timedelta(hours=6)
            )
            st.rerun()
    with ctrl_col3:
        st.session_state.window_span_hours = st.selectbox(
            "Window Width:",
            options=[6, 12, 24, 72, 168, 720],
            index=2,
            format_func=lambda h: f"{h} Hours" if h < 24 else f"{h//24} Day{'s' if h > 24 else ''}"
        )
    with ctrl_col4:
        daytime_only = st.checkbox("☀️ Daytime Only (06-19h)", value=False)
    with ctrl_col5:
        if st.button("+6 Hours ▶"):
            st.session_state.window_end_time = min(
                t_global_max.to_pydatetime(),
                st.session_state.window_end_time + datetime.timedelta(hours=6)
            )
            st.rerun()
    with ctrl_col6:
        if st.button("🔴 Live Latest"):
            st.session_state.window_end_time = t_global_max.to_pydatetime()
            st.rerun()

    span_h = st.session_state.window_span_hours
    min_slider = (t_global_min + pd.Timedelta(hours=span_h)).to_pydatetime()
    max_slider = t_global_max.to_pydatetime()

    if span_h >= 720:
        slider_freq = "2h"
        resample_rule = "2h"
    elif span_h >= 168:
        slider_freq = "30min"
        resample_rule = "30min"
    elif span_h >= 72:
        slider_freq = "20min"
        resample_rule = "20min"
    else:
        slider_freq = "15min"
        resample_rule = None

    v_end = min(pd.to_datetime(st.session_state.window_end_time), t_global_max)
    v_start = v_end - pd.Timedelta(hours=span_h)

    date_header_str = f"{v_start.strftime('%a %d.%m. %H:%M')} – {v_end.strftime('%a %d.%m. %H:%M')}"
    st.markdown(
        f'<div class="slider-month-pill">📅 <span><b>{date_header_str}</b></span> ({span_h}h View)</div>',
        unsafe_allow_html=True
    )

    if min_slider < max_slider:
        timeline_ticks = pd.date_range(start=min_slider, end=max_slider, freq=slider_freq).to_pydatetime().tolist()
        if not timeline_ticks or timeline_ticks[-1] != max_slider:
            timeline_ticks.append(max_slider)

        curr_target = min(max_slider, max(min_slider, st.session_state.window_end_time))
        closest_idx = int(np.argmin([abs((t - curr_target).total_seconds()) for t in timeline_ticks]))

        selected_slider_idx = st.select_slider(
            "Scroll Active Timeline Window:",
            options=range(len(timeline_ticks)),
            value=closest_idx,
            format_func=lambda idx: timeline_ticks[idx].strftime("%a %d.%m. %H:%M")
        )

        chosen_dt = timeline_ticks[selected_slider_idx]
        if abs((chosen_dt - st.session_state.window_end_time).total_seconds()) > 60:
            st.session_state.window_end_time = chosen_dt
            st.rerun()

    df_slice = df_all[(df_all["timestamp"] >= v_start) & (df_all["timestamp"] <= v_end)].copy()

    if daytime_only:
        df_slice = df_slice[df_slice["timestamp"].dt.hour.between(6, 18)].copy()

    if df_slice.empty:
        st.warning("No records in selected window.")
        df_slice = df_all.tail(20).copy()

    if resample_rule is not None and not df_slice.empty:
        df_agg = df_slice.set_index("timestamp").resample(resample_rule).agg({
            "velocita_knots": "mean",
            "raffica_knots": "max",
            "direzione_deg": "mean",
            "temperatura_c": "mean"
        })
        df_resampled = df_agg.interpolate(method="time", limit=3).dropna(subset=["velocita_knots"]).reset_index()
        df_resampled["direzione_cardinal"] = df_resampled["direzione_deg"].apply(deg_to_cardinal)
        df_slice = df_resampled

    df_slice["velocita_bft"] = knots_to_bft(df_slice["velocita_knots"])
    df_slice["raffica_bft"] = knots_to_bft(df_slice["raffica_knots"])
    df_slice["velocita_plot_y"] = bft_to_stretched(df_slice["velocita_bft"])
    df_slice["raffica_plot_y"] = bft_to_stretched(df_slice["raffica_bft"])
    df_slice["arrow_angle"] = (df_slice["direzione_deg"].fillna(0) + 180) % 360

    has_temp = "temperatura_c" in df_slice.columns and df_slice["temperatura_c"].notnull().any()
    df_plot_lines = df_slice.sort_values("timestamp").reset_index(drop=True)
    df_plot_lines["raffica_plot_y"] = pd.to_numeric(df_plot_lines["raffica_plot_y"], errors="coerce")

    max_observed_y = df_plot_lines["raffica_plot_y"].dropna().max() if not df_plot_lines["raffica_plot_y"].dropna().empty else bft_to_stretched(7.5)
    top_y_limit = max(bft_to_stretched(7.5), max_observed_y * 1.14)

    # Dynamic Labels & Arrow Vectors
    speed_labels = [""] * len(df_plot_lines)
    gust_labels = [""] * len(df_plot_lines)
    labeled_speed_points = []

    valid_mask = df_plot_lines["velocita_knots"].notnull()
    valid_indices = df_plot_lines.index[valid_mask].tolist()

    if valid_indices:
        f_idx = valid_indices[0]
        v0 = df_plot_lines.loc[f_idx, 'velocita_knots']
        d0 = df_plot_lines.loc[f_idx, 'direzione_deg']
        speed_labels[f_idx] = f"{v0:.1f}"
        labeled_speed_points.append({
            "timestamp": df_plot_lines.loc[f_idx, 'timestamp'],
            "velocita_plot_y": df_plot_lines.loc[f_idx, 'velocita_plot_y'],
            "direzione_deg": d0
        })

        last_s_val = v0
        last_s_idx = f_idx
        last_g_val = df_plot_lines.loc[f_idx, 'raffica_knots'] if pd.notnull(df_plot_lines.loc[f_idx, 'raffica_knots']) else -999.0
        last_g_idx = f_idx

        v_arr = df_plot_lines["velocita_knots"].to_numpy()
        r_arr = df_plot_lines["raffica_knots"].to_numpy()
        d_arr = df_plot_lines["direzione_deg"].to_numpy()
        y_arr = df_plot_lines["velocita_plot_y"].to_numpy()
        t_arr = df_plot_lines["timestamp"].to_numpy()

        if span_h >= 720:
            min_pts_step, max_pts_step, delta_threshold = 10, 30, 4.0
        elif span_h >= 168:
            min_pts_step, max_pts_step, delta_threshold = 6, 20, 2.5
        elif span_h >= 72:
            min_pts_step, max_pts_step, delta_threshold = 4, 14, 2.0
        else:
            min_pts_step, max_pts_step, delta_threshold = 2, 8, 1.0

        for idx in valid_indices[1:]:
            curr_v, curr_d, curr_g = v_arr[idx], d_arr[idx], r_arr[idx]
            delta_s = abs(curr_v - last_s_val)
            pts_since_s = idx - last_s_idx

            if (delta_s >= delta_threshold and pts_since_s >= min_pts_step) or pts_since_s >= max_pts_step:
                speed_labels[idx] = f"{curr_v:.1f}"
                labeled_speed_points.append({
                    "timestamp": t_arr[idx],
                    "velocita_plot_y": y_arr[idx],
                    "direzione_deg": curr_d
                })
                last_s_val, last_s_idx = curr_v, idx

            if pd.notnull(curr_g):
                delta_g = abs(curr_g - last_g_val)
                pts_since_g = idx - last_g_idx
                if (delta_g >= delta_threshold and pts_since_g >= min_pts_step) or pts_since_g >= max_pts_step:
                    gust_labels[idx] = f"{curr_g:.1f}"
                    last_g_val, last_g_idx = curr_g, idx

    df_plot_lines["speed_label"] = speed_labels
    df_plot_lines["gust_label"] = gust_labels

    fig = make_subplots(
        rows=3 if has_temp else 2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        subplot_titles=(
            "<b>Wind speed and gusts (Stretched Beaufort Scale)</b>",
            "<b>Wind direction</b>",
            "<b>Temperature (°C)</b>" if has_temp else None
        ),
        row_heights=[0.54, 0.28, 0.A `SyntaxError` right on an `else:` statement is very common in Python. Because Python relies strictly on indentation and structure, this error almost always means the parser got confused by something right at that line or just above it. 

Here are the most common culprits to check around **line 798** in your `app.py` file:

*   **Indentation Mismatch:** The `else:` keyword must align vertically with its corresponding `if`, `for`, `while`, or `try` statement. If you mixed tabs and spaces, or if the indentation is off by even one space, Python will throw this error.
*   **Missing or Broken Preceding Statement:** Ensure there is a valid `if` (or other block) directly above it, and that the `if` line ends with a colon (`:`). If the `if` block is empty, you must use the `pass` keyword inside it.
*   **Unclosed Parentheses, Brackets, or Quotes Above:** If you have an unclosed bracket (`(`, `[`, `{`) or an open string somewhere on the lines just before 798, Python’s parser loses track of where it is and often flags the `else:` as the exact spot where things finally break.
*   **A Rogue Semicolon or Character:** Look closely at the end of the line immediately preceding `else:` to ensure no accidental typos broke the syntax.

**How to fix it:**
Take a quick look at lines 790 through 802 in your code. If you'd like to paste that snippet here, I'd be happy to take a look and help you spot the exact typo!
