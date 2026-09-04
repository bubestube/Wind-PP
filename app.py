import datetime
import math
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

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
    /* Maximize canvas on mobile */
    .block-container {
        padding-top: 0.8rem !important;
        padding-bottom: 1.2rem !important;
        padding-left: 0.4rem !important;
        padding-right: 0.4rem !important;
    }
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    
    /* Responsive compact cards */
    .wg-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 6px 8px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        text-align: center;
        margin-bottom: 6px;
    }
    .wg-card-title {
        font-size: 0.68rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748b;
        margin-bottom: 2px;
    }
    .wg-card-val {
        font-size: 1.2rem;
        font-weight: 700;
        font-family: monospace;
    }

    div.stButton > button {
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        padding: 4px 6px !important;
        font-size: 0.78rem !important;
        width: 100% !important;
        white-space: nowrap !important;
    }
    div.stButton > button:hover {
        background-color: #f8fafc !important;
        border-color: #94a3b8 !important;
        color: #0284c7 !important;
    }

    div[data-testid="stSelectbox"] label p {
        color: #475569 !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
    }
    div[data-testid="stSelectbox"] div[role="combobox"] {
        background-color: #f1f5f9 !important;
        color: #0f172a !important;
        border-color: #cbd5e1 !important;
        border-radius: 6px !important;
        min-height: 32px !important;
        font-size: 0.82rem !important;
    }

    .slider-month-pill {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        background-color: #ffffff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 3px 10px;
        font-size: 0.80rem;
        font-weight: 600;
        color: #0f172a;
        margin-top: 4px;
        margin-bottom: 2px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    /* Force horizontal alignment of buttons on mobile screens */
    div[data-testid="stHorizontalBlock"]:has(.mobile-nav-btn) {
        display: flex !important;
        flex-direction: row !important;
        flex-wrap: nowrap !important;
        gap: 4px !important;
        margin-bottom: 4px !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.mobile-nav-btn) > div {
        flex: 1 1 0px !important;
        min-width: 0 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.mobile-nav-btn) div[data-testid="stButton"] {
        width: 100% !important;
    }
    </style>
""", unsafe_allow_html=True)

header_left, header_right = st.columns([3, 1])
with header_left:
    st.title("🪁 Porto Pollo Live")
with header_right:
    components.html("""
        <style>
          #fsBtn {
            width: 100%;
            height: 34px;
            margin-top: 14px;
            background-color: #ffffff;
            color: #0f172a;
            border: 1px solid #cbd5e1;
            border-radius: 6px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            font-weight: 600;
            font-size: 0.80rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
            transition: background-color 0.15s ease, border-color 0.15s ease;
          }
          #fsBtn:hover {
            background-color: #f8fafc;
            border-color: #94a3b8;
            color: #0284c7;
          }
        </style>
        <button id="fsBtn"><span>⛶</span> Fullscreen</button>
        <script>
          const btn = document.getElementById('fsBtn');
          btn.addEventListener('click', function () {
            const rootDoc = window.parent.document;
            const targetEl = rootDoc.documentElement;
            const isFs = rootDoc.fullscreenElement || 
                         rootDoc.webkitFullscreenElement || 
                         rootDoc.mozFullScreenElement || 
                         rootDoc.msFullscreenElement;

            if (!isFs) {
              if (targetEl.requestFullscreen) { targetEl.requestFullscreen(); }
              else if (targetEl.webkitRequestFullscreen) { targetEl.webkitRequestFullscreen(); }
              else if (targetEl.mozRequestFullScreen) { targetEl.mozRequestFullScreen(); }
              else if (targetEl.msRequestFullscreen) { targetEl.msRequestFullscreen(); }
              btn.innerHTML = '<span>✕</span> Exit';
            } else {
              if (rootDoc.exitFullscreen) { rootDoc.exitFullscreen(); }
              else if (rootDoc.webkitExitFullscreen) { rootDoc.webkitExitFullscreen(); }
              else if (rootDoc.mozCancelFullScreen) { rootDoc.mozCancelFullScreen(); }
              else if (rootDoc.msExitFullscreen) { rootDoc.msExitFullscreen(); }
              btn.innerHTML = '<span>⛶</span> Fullscreen';
            }
          });
        </script>
    """, height=50)

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

    # Mobile-friendly 3 + 2 KPI Grid
    kpi_row1 = st.columns(3)
    with kpi_row1[0]:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">💨 Wind</div>
            <div class="wg-card-val" style="color:{speed_fg}; background:{speed_bg}; border-radius:4px; padding:1px;">
                {latest_bft:.1f} <span style="font-size:0.75rem;">Bft</span>
            </div>
        </div>""", unsafe_allow_html=True)
    with kpi_row1[1]:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">💨 Gust</div>
            <div class="wg-card-val" style="color:{gust_fg}; background:{gust_bg}; border-radius:4px; padding:1px;">
                {latest['raffica_knots']:.0f} <span style="font-size:0.75rem;">kts</span>
            </div>
        </div>""", unsafe_allow_html=True)
    with kpi_row1[2]:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">🧭 Dir</div>
            <div class="wg-card-val" style="color:#0f172a;">
                {latest['direzione_cardinal']} <span style="font-size:0.8rem; color:#64748b;">({latest['direzione_deg']:.0f}°)</span>
            </div>
        </div>""", unsafe_allow_html=True)

    kpi_row2 = st.columns(2)
    with kpi_row2[0]:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">🌡️ Temp</div>
            <div class="wg-card-val" style="color:#ca8a04;">
                {f"{temp_val:.1f} °C" if pd.notnull(temp_val) else "N/A"}
            </div>
        </div>""", unsafe_allow_html=True)
    with kpi_row2[1]:
        st.markdown(f"""<div class="wg-card">
            <div class="wg-card-title">⏱️ Updated</div>
            <div class="wg-card-val" style="font-size:0.95rem; padding-top:4px; color:#334155;">
                {latest['timestamp'].strftime('%d.%m. %H:%M')}
            </div>
        </div>""", unsafe_allow_html=True)

    if "window_end_time" not in st.session_state:
        st.session_state.window_end_time = t_global_max.to_pydatetime()
    if "window_span_hours" not in st.session_state:
        st.session_state.window_span_hours = 12

    # Width selector
    st.session_state.window_span_hours = st.selectbox(
        "Window Width:",
        options=[6, 12, 24, 72, 168, 720],
        index=1,
        format_func=lambda h: f"{h}h" if h < 24 else f"{h//24}d"
    )

    # Horizontal navigation button bar
    btn_cols = st.columns(5)
    with btn_cols[0]:
        st.markdown('<div class="mobile-nav-btn"></div>', unsafe_allow_html=True)
        if st.button("◀ -1d"):
            st.session_state.window_end_time = max(
                (t_global_min + pd.Timedelta(hours=st.session_state.window_span_hours)).to_pydatetime(),
                st.session_state.window_end_time - datetime.timedelta(days=1)
            )
            st.rerun()
    with btn_cols[1]:
        st.markdown('<div class="mobile-nav-btn"></div>', unsafe_allow_html=True)
        if st.button("◀ -6h"):
            st.session_state.window_end_time = max(
                (t_global_min + pd.Timedelta(hours=st.session_state.window_span_hours)).to_pydatetime(),
                st.session_state.window_end_time - datetime.timedelta(hours=6)
            )
            st.rerun()
    with btn_cols[2]:
        st.markdown('<div class="mobile-nav-btn"></div>', unsafe_allow_html=True)
        if st.button("+6h ▶"):
            st.session_state.window_end_time = min(
                t_global_max.to_pydatetime(),
                st.session_state.window_end_time + datetime.timedelta(hours=6)
            )
            st.rerun()
    with btn_cols[3]:
        st.markdown('<div class="mobile-nav-btn"></div>', unsafe_allow_html=True)
        if st.button("+1d ▶"):
            st.session_state.window_end_time = min(
                t_global_max.to_pydatetime(),
                st.session_state.window_end_time + datetime.timedelta(days=1)
            )
            st.rerun()
    with btn_cols[4]:
        st.markdown('<div class="mobile-nav-btn"></div>', unsafe_allow_html=True)
        if st.button("🔴 Live"):
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
            "Timeline Window:",
            options=range(len(timeline_ticks)),
            value=closest_idx,
            label_visibility="collapsed",
            format_func=lambda idx: timeline_ticks[idx].strftime("%a %d.%m. %H:%M")
        )

        chosen_dt = timeline_ticks[selected_slider_idx]
        if abs((chosen_dt - st.session_state.window_end_time).total_seconds()) > 60:
            st.session_state.window_end_time = chosen_dt
            st.rerun()

    df_slice = df_all[(df_all["timestamp"] >= v_start) & (df_all["timestamp"] <= v_end)].copy()

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
            min_pts_step, max_pts_step, delta_threshold = 12, 35, 4.5
        elif span_h >= 168:
            min_pts_step, max_pts_step, delta_threshold = 8, 24, 3.0
        elif span_h >= 72:
            min_pts_step, max_pts_step, delta_threshold = 5, 16, 2.5
        else:
            min_pts_step, max_pts_step, delta_threshold = 3, 10, 1.5

        for idx in valid_indices[1:]:
            curr_v, curr_d, curr_g = v_arr[idx], d_arr[idx], r_arr[idx]
            delta_s = abs(curr_v - last_s_val)
            pts_since_s = idx - last_s_idx

            if (delta_s >= delta_threshold and pts_since_s >= min_pts_step) or pts_since_s >= max_pts_step:
                speed_labels[idx] = f"{curr_v:.0f}"
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
                    gust_labels[idx] = f"{curr_g:.0f}"
                    last_g_val, last_g_idx = curr_g, idx

    df_plot_lines["speed_label"] = speed_labels
    df_plot_lines["gust_label"] = gust_labels

    subplot_titles_list = ["", "<b>Direction</b>"]
    if has_temp:
        subplot_titles_list.append("<b>Temp (°C)</b>")

    fig = make_subplots(
        rows=3 if has_temp else 2,
        cols=1,
        shared_xaxes=False,
        vertical_spacing=0.032,
        subplot_titles=tuple(subplot_titles_list),
        row_heights=[0.68, 0.18, 0.14] if has_temp else [0.78, 0.22]
    )

    # --- TRUE CONTINUOUS 2D HORIZONTAL GRADIENT SURFACE ---
    y_levels = np.linspace(0, top_y_limit, 200)
    bft_levels = np.power(y_levels, 1.0 / BFT_EXP)
    z_gradient = np.tile(bft_levels, (2, 1)).T

    fig.add_trace(go.Heatmap(
        x=[v_start, v_end],
        y=y_levels,
        z=z_gradient,
        colorscale=WIND_COLORSCALE_SMOOTH,
        zmin=0,
        zmax=8,
        zsmooth='best',
        showscale=False,
        hoverinfo="skip"
    ), row=1, col=1)

    # --- INVERTED MASK: BLOCKS OUT EVERYTHING ABOVE GUST LINE ---
    x_mask = [v_start] + list(df_plot_lines["timestamp"]) + [v_end, v_end, v_start]
    y_mask = [df_plot_lines["raffica_plot_y"].iloc[0]] + list(df_plot_lines["raffica_plot_y"]) + [
        df_plot_lines["raffica_plot_y"].iloc[-1], top_y_limit * 1.05, top_y_limit * 1.05
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

    # --- PERFECT RECTANGULAR NIGHT SHADING BOXES ---
    day_cursor = v_start.floor("D")
    while day_cursor <= v_end + pd.Timedelta(days=2):
        night_start = day_cursor + pd.Timedelta(hours=19)
        night_end = day_cursor + pd.Timedelta(days=1, hours=6)
        if night_start < v_end and night_end > v_start:
            x_left = max(night_start, v_start)
            x_right = min(night_end, v_end)

            fig.add_trace(go.Scatter(
                x=[x_left, x_right, x_right, x_left, x_left],
                y=[0, 0, top_y_limit * 1.05, top_y_limit * 1.05, 0],
                fill="toself",
                fillcolor="rgba(148, 163, 184, 0.22)",
                line=dict(color="rgba(0,0,0,0)", width=0),
                hoverinfo="skip",
                showlegend=False
            ), row=1, col=1)

            fig.add_trace(go.Scatter(
                x=[x_left, x_right, x_right, x_left, x_left],
                y=[-35, -35, 395, 395, -35],
                fill="toself",
                fillcolor="rgba(148, 163, 184, 0.22)",
                line=dict(color="rgba(0,0,0,0)", width=0),
                hoverinfo="skip",
                showlegend=False
            ), row=2, col=1)

            if has_temp:
                t_min = df_plot_lines["temperatura_c"].min()
                t_max = df_plot_lines["temperatura_c"].max()
                t_pad = max(2.0, (t_max - t_min) * 0.1) if pd.notnull(t_min) and pd.notnull(t_max) else 5.0
                fig.add_trace(go.Scatter(
                    x=[x_left, x_right, x_right, x_left, x_left],
                    y=[(t_min - t_pad) if pd.notnull(t_min) else 0,
                       (t_min - t_pad) if pd.notnull(t_min) else 0,
                       (t_max + t_pad) if pd.notnull(t_max) else 40,
                       (t_max + t_pad) if pd.notnull(t_max) else 40,
                       (t_min - t_pad) if pd.notnull(t_min) else 0],
                    fill="toself",
                    fillcolor="rgba(148, 163, 184, 0.22)",
                    line=dict(color="rgba(0,0,0,0)", width=0),
                    hoverinfo="skip",
                    showlegend=False
                ), row=3, col=1)

        day_cursor += pd.Timedelta(days=1)

    # Subplot 1: Gust Trace
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["raffica_plot_y"],
        text=df_plot_lines["gust_label"],
        textposition="top center",
        textfont=dict(family="Arial, sans-serif", size=9.0, color="#b91c1c"),
        customdata=np.stack((df_plot_lines["raffica_bft"], df_plot_lines["raffica_knots"]), axis=-1),
        mode="lines+markers+text",
        name="Gust",
        connectgaps=True,
        line=dict(color="#0f172a", width=1.4, dash="dot"),
        marker=dict(symbol="circle", size=3.0, color="#0f172a"),
        hovertemplate="<b>Gust:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=1, col=1)

    # Subplot 1: Sustained Speed Trace
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["velocita_plot_y"],
        text=df_plot_lines["speed_label"],
        textposition="bottom center",
        textfont=dict(family="Arial, sans-serif", size=9.0, color="#0f172a"),
        customdata=np.stack((df_plot_lines["velocita_bft"], df_plot_lines["velocita_knots"], df_plot_lines["direzione_deg"]), axis=-1),
        mode="lines+markers+text",
        name="Speed",
        connectgaps=True,
        line=dict(color="#0f172a", width=2.0),
        marker=dict(size=3.0, color="#0f172a"),
        hovertemplate="<b>Speed:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<br><b>Dir:</b> %{customdata[2]:.0f}°<extra></extra>"
    ), row=1, col=1)

    # Stemmed mini vector arrows
    mini_arrow_len = 16
    for pt in labeled_speed_points:
        deg = pt["direzione_deg"]
        if pd.isna(deg) or pd.isna(pt["velocita_plot_y"]):
            continue

        angle_rad = math.radians((float(deg) + 180.0) % 360.0)
        dx = mini_arrow_len * math.sin(angle_rad)
        dy = mini_arrow_len * math.cos(angle_rad)

        fig.add_annotation(
            x=pt["timestamp"],
            y=pt["velocita_plot_y"],
            xref="x1",
            yref="y1",
            yshift=-20,
            ax=-dx,
            ay=dy,
            axref="pixel",
            ayref="pixel",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.2,
            arrowwidth=1.2,
            arrowcolor="#0f172a",
            opacity=0.9
        )

    # Subplot 2: Direction Trace
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["direzione_deg"],
        mode="markers",
        name="Dir",
        connectgaps=False,
        marker=dict(symbol="circle", size=2.5, color="#64748b"),
        customdata=df_plot_lines[["direzione_cardinal", "velocita_knots", "velocita_bft"]],
        hovertemplate="<b>Dir:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[2]:.1f} Bft<extra></extra>"
    ), row=2, col=1)

    # Subplot 2: Direction Arrows (reduced density for small displays)
    df_for_arrows = df_slice.sort_values("timestamp").reset_index(drop=True)
    df_for_arrows["arrow_angle"] = (df_for_arrows["direzione_deg"].fillna(0) + 180) % 360

    target_arrow_count = 10 if span_h >= 720 else (14 if span_h >= 72 else 18)
    steady_step = max(4, len(df_for_arrows) // target_arrow_count)
    selected_indices = []
    if not df_for_arrows.empty:
        selected_indices.append(0)
        last_idx = 0
        last_deg = df_for_arrows.loc[0, "direzione_deg"]

        for i in range(1, len(df_for_arrows)):
            curr_deg = df_for_arrows.loc[i, "direzione_deg"]
            if pd.isna(curr_deg):
                continue
            delta_deg = abs((curr_deg - last_deg + 180) % 360 - 180)
            points_since_last = i - last_idx

            angle_sens = 45.0 if span_h >= 720 else 30.0
            if delta_deg > angle_sens or points_since_last >= steady_step:
                selected_indices.append(i)
                last_idx = i
                last_deg = curr_deg

    df_sub = df_for_arrows.iloc[selected_indices]
    arrow_length_px = 28

    for _, row_data in df_sub.iterrows():
        angle_deg = row_data["arrow_angle"]
        speed_val = row_data["velocita_knots"]

        if pd.isna(angle_deg) or pd.isna(row_data["direzione_deg"]):
            continue

        arrow_color = "#16a34a" if (pd.notnull(speed_val) and speed_val >= 18.0) else "#dc2626"
        rad = math.radians(angle_deg)
        dx = arrow_length_px * math.sin(rad)
        dy = arrow_length_px * math.cos(rad)

        fig.add_annotation(
            x=row_data["timestamp"],
            y=row_data["direzione_deg"],
            xref="x2",
            yref="y2",
            ax=-dx,
            ay=dy,
            axref="pixel",
            ayref="pixel",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.6,
            arrowwidth=1.3,
            arrowcolor=arrow_color,
            opacity=0.9
        )

    # Subplot 3: Temperature (Segmented Lines: Day Yellow, Night 19-06h Dark Blue)
    if has_temp:
        m_size = 2.5
        l_width = 1.8

        is_day_point = df_plot_lines["timestamp"].dt.hour.between(6, 18)
        point_colors = ["#eab308" if day else "#1e3a8a" for day in is_day_point]

        t_series = df_plot_lines["timestamp"].to_numpy()
        y_series = df_plot_lines["temperatura_c"].to_numpy()

        day_x, day_y = [], []
        night_x, night_y = [], []

        for i in range(len(df_plot_lines) - 1):
            t1 = pd.Timestamp(t_series[i])
            t2 = pd.Timestamp(t_series[i + 1])
            y1, y2 = y_series[i], y_series[i + 1]

            if pd.isna(y1) or pd.isna(y2):
                continue

            t_mid = t1 + (t2 - t1) / 2
            is_segment_night = not (6 <= t_mid.hour < 19)

            if is_segment_night:
                night_x.extend([t1, t2, None])
                night_y.extend([y1, y2, None])
            else:
                day_x.extend([t1, t2, None])
                day_y.extend([y1, y2, None])

        if day_x:
            fig.add_trace(go.Scatter(
                x=day_x,
                y=day_y,
                mode="lines",
                line=dict(color="#eab308", width=l_width),
                hoverinfo="skip",
                showlegend=False
            ), row=3, col=1)

        if night_x:
            fig.add_trace(go.Scatter(
                x=night_x,
                y=night_y,
                mode="lines",
                line=dict(color="#1e3a8a", width=l_width),
                hoverinfo="skip",
                showlegend=False
            ), row=3, col=1)

        fig.add_trace(go.Scatter(
            x=df_plot_lines["timestamp"],
            y=df_plot_lines["temperatura_c"],
            mode="markers",
            name="Temp",
            marker=dict(size=m_size, color=point_colors),
            hovertemplate="<b>Temp:</b> %{y:.1f} °C<extra></extra>"
        ), row=3, col=1)

        fig.update_yaxes(
            title_text="",
            tickfont=dict(color="#0f172a", size=9),
            showline=False,
            gridcolor="#cbd5e1",
            fixedrange=True,
            row=3, col=1
        )

    # Midnight dividers & in-graph headers
    day_cursor = v_start.floor("D")
    while day_cursor <= v_end + pd.Timedelta(days=1):
        midnight = day_cursor
        if v_start <= midnight <= v_end:
            fig.add_vline(
                x=midnight,
                line_width=1.0,
                line_dash="dash",
                line_color="#64748b",
                opacity=0.6
            )
            fig.add_annotation(
                x=midnight + pd.Timedelta(minutes=30),
                y=top_y_limit * 0.95,
                xref="x1",
                yref="y1",
                text=f"<b>{midnight.strftime('%a %d')}</b>",
                showarrow=False,
                font=dict(size=9, color="#334155"),
                bgcolor="rgba(255, 255, 255, 0.85)",
                bordercolor="#cbd5e1",
                borderwidth=1,
                borderpad=1,
                xanchor="left"
            )
        day_cursor += pd.Timedelta(days=1)

    # Compact Beaufort scale tick labels for mobile widths
    bft_ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    bft_stretched_vals = [bft_to_stretched(b) for b in bft_ticks]
    bft_labels_compact = [f"{b} Bft" for b in bft_ticks]

    fig.update_yaxes(
        title_text="",
        range=[0, top_y_limit],
        tickvals=bft_stretched_vals,
        ticktext=bft_labels_compact,
        tickfont=dict(color="#0f172a", size=9.5),
        showline=False,
        gridcolor="#cbd5e1",
        zerolinecolor="#cbd5e1",
        fixedrange=True,
        row=1, col=1
    )

    fig.update_yaxes(
        title_text="",
        range=[-35, 395],
        tickvals=[0, 90, 180, 270, 360],
        ticktext=["N", "E", "S", "W", "N"],
        tickfont=dict(color="#0f172a", size=9.5),
        showline=False,
        gridcolor="#cbd5e1",
        fixedrange=True,
        row=2, col=1
    )

    if span_h >= 720:
        dtick_val = 24 * 3600 * 1000
        tick_format_str = "%d.%m."
    elif span_h >= 168:
        dtick_val = 12 * 3600 * 1000
        tick_format_str = "%H:%M<br>%a"
    elif span_h >= 72:
        dtick_val = 6 * 3600 * 1000
        tick_format_str = "%H:%M<br>%a"
    elif span_h >= 24:
        dtick_val = 3 * 3600 * 1000
        tick_format_str = "%H:%M"
    else:
        dtick_val = 1 * 3600 * 1000
        tick_format_str = "%H:%M"

    fig.update_xaxes(
        range=[v_start, v_end],
        gridcolor="#cbd5e1",
        showgrid=True,
        dtick=dtick_val,
        tickformat=tick_format_str,
        tickfont=dict(color="#0f172a", size=9, family="Arial, sans-serif"),
        showline=False,
        fixedrange=True,
        side="top",
        row=1, col=1
    )

    for r in range(2, (4 if has_temp else 3)):
        fig.update_xaxes(
            range=[v_start, v_end],
            showticklabels=False,
            fixedrange=True,
            row=r, col=1
        )

    fig.update_layout(
        height=680 if has_temp else 520,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        font=dict(color="#1e293b", family="Arial, sans-serif"),
        dragmode=False,
        hovermode="x unified",
        showlegend=False,
        margin=dict(l=22, r=10, t=30, b=15)
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": False,
            "displayModeBar": False,
            "staticPlot": False
        }
    )

    with st.expander("📋 View Data Log"):
        st.dataframe(
            df_slice.sort_values("timestamp", ascending=False),
            use_container_width=True
        )
else:
    st.info("No data file found yet.")
