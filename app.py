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
        padding: 4px 12px;
        font-size: 0.88rem;
        font-weight: 600;
        color: #0f172a;
        margin-bottom: 4px;
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

    # Top KPI Badges
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

    # Viewport State
    if "window_end_time" not in st.session_state:
        st.session_state.window_end_time = t_global_max.to_pydatetime()
    if "window_span_hours" not in st.session_state:
        st.session_state.window_span_hours = 6

    window_options = [6, 12, 24, 72, 168, 720]
    curr_span = st.session_state.get("window_span_hours", 6)
    curr_idx = window_options.index(curr_span) if curr_span in window_options else 0

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

    # --- Tiered Density Reduction Rules ---
    if span_h >= 720:          # 30 Days: 2-hour buckets
        resample_rule = "2h"
        slider_step_delta = datetime.timedelta(hours=2)
    elif span_h >= 168:        # 7 Days: 30-minute buckets
        resample_rule = "30min"
        slider_step_delta = datetime.timedelta(minutes=30)
    elif span_h >= 72:         # 3 Days: 20-minute buckets
        resample_rule = "20min"
        slider_step_delta = datetime.timedelta(minutes=20)
    else:                      # <= 1 Day: Raw native resolution
        resample_rule = None
        slider_step_delta = datetime.timedelta(minutes=15)

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

    # Active Month Badge
    cur_end = pd.to_datetime(st.session_state.window_end_time)
    cur_start = cur_end - pd.Timedelta(hours=span_h)
    month_str = cur_end.strftime("%B %Y") if cur_start.strftime("%B %Y") == cur_end.strftime("%B %Y") else f"{cur_start.strftime('%B')} – {cur_end.strftime('%B %Y')}"
    st.markdown(
        f'<div class="slider-month-pill">📅 <span>{month_str}</span> (Step & Bucket: {resample_rule if resample_rule else "Native ~3m"})</div>',
        unsafe_allow_html=True
    )

    if min_allowable_end < max_allowable_end:
        scrub_pos = st.slider(
            "Scroll Active Timeline Window:",
            min_value=min_allowable_end,
            max_value=max_allowable_end,
            value=min(max_allowable_end, max(min_allowable_end, st.session_state.window_end_time)),
            format="DD.MM HH:mm",
            step=slider_step_delta
        )
        if scrub_pos != st.session_state.window_end_time:
            st.session_state.window_end_time = scrub_pos
            st.rerun()

    v_end = pd.to_datetime(st.session_state.window_end_time)
    v_start = v_end - pd.Timedelta(hours=span_h)

    # Slice only the active window + 2h margin to keep resampling fast
    buffer = pd.Timedelta(hours=2)
    df_slice = df_raw[(df_raw["timestamp"] >= v_start - buffer) & (df_raw["timestamp"] <= v_end + buffer)].copy()

    if daytime_only:
        df_slice = df_slice[df_slice["timestamp"].dt.hour.between(6, 18)].copy()

    if df_slice.empty:
        df_slice = df_raw.tail(40).copy()

    # Apply tiered resampling
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
    top_y_limit = max(bft_to_stretched(7.5), max_observed_y * 1.15)

    # Adaptive Text Labels & Mini Stemmed Vectors (Subplot 1)
    speed_labels = [""] * len(df_chart)
    gust_labels = [""] * len(df_chart)
    labeled_speed_points = []

    valid_mask = df_chart["velocita_knots"].notnull()
    valid_indices = df_chart.index[valid_mask].tolist()

    if valid_indices:
        f_idx = valid_indices[0]
        v0 = df_chart.loc[f_idx, 'velocita_knots']
        d0 = df_chart.loc[f_idx, 'direzione_deg']
        speed_labels[f_idx] = f"{v0:.1f}"
        labeled_speed_points.append({
            "timestamp": df_chart.loc[f_idx, 'timestamp'],
            "velocita_plot_y": df_chart.loc[f_idx, 'velocita_plot_y'],
            "direzione_deg": d0
        })

        last_s_val = v0
        last_s_idx = f_idx
        last_g_val = df_chart.loc[f_idx, 'raffica_knots'] if pd.notnull(df_chart.loc[f_idx, 'raffica_knots']) else -999.0
        last_g_idx = f_idx

        v_arr = df_chart["velocita_knots"].to_numpy()
        r_arr = df_chart["raffica_knots"].to_numpy()
        d_arr = df_chart["direzione_deg"].to_numpy()
        y_arr = df_chart["velocita_plot_y"].to_numpy()
        t_arr = df_chart["timestamp"].to_numpy()

        if span_h >= 720:
            min_pts_step = 10
            max_pts_step = 30
            delta_threshold = 4.0
        elif span_h >= 168:
            min_pts_step = 6
            max_pts_step = 20
            delta_threshold = 2.5
        elif span_h >= 72:
            min_pts_step = 4
            max_pts_step = 14
            delta_threshold = 2.0
        else:
            min_pts_step = 2
            max_pts_step = 8
            delta_threshold = 1.0

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

    df_chart["speed_label"] = speed_labels
    df_chart["gust_label"] = gust_labels

    # 4. Multi-Panel Subplots
    fig = make_subplots(
        rows=3 if has_temp else 2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        subplot_titles=(
            f"<b>Wind speed and gusts (Stretched Beaufort Scale) – {v_start.strftime('%d.%m %H:%M')} to {v_end.strftime('%d.%m %H:%M')}</b>",
            "<b>Wind direction & Vectors</b>",
            "<b>Temperature (°C)</b>" if has_temp else None
        ),
        row_heights=[0.54, 0.28, 0.18] if has_temp else [0.65, 0.35]
    )

    # Continuous 2D Background Gradient Surface
    y_levels = np.linspace(0, top_y_limit, 45)
    bft_levels = np.power(y_levels, 1.0 / BFT_EXP)
    z_gradient = np.tile(bft_levels, (2, 1)).T

    fig.add_trace(go.Heatmap(
        x=[v_start, v_end],
        y=y_levels,
        z=z_gradient,
        colorscale=WIND_COLORSCALE_SMOOTH,
        zmin=0,
        zmax=8,
        showscale=False,
        hoverinfo="skip"
    ), row=1, col=1)

    # Inverted White Ceiling Mask
    x_mask = [v_start] + list(df_chart["timestamp"]) + [v_end, v_end, v_start]
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

    # Subplot 1: Gust Trace
    fig.add_trace(go.Scatter(
        x=df_chart["timestamp"],
        y=df_chart["raffica_plot_y"],
        text=df_chart["gust_label"],
        textposition="top center",
        textfont=dict(family="Arial, sans-serif", size=9.5 if span_h >= 720 else 10.0, color="#b91c1c"),
        customdata=np.stack((df_chart["raffica_bft"], df_chart["raffica_knots"]), axis=-1),
        mode="lines+markers+text",
        name="Gust (Raffica)",
        line=dict(color="#0f172a", width=1.4 if span_h >= 720 else 1.6, dash="dot"),
        marker=dict(symbol="circle", size=3.0 if span_h >= 720 else (3.5 if span_h >= 72 else 4.0), color="#0f172a"),
        hovertemplate="<b>Gust:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=1, col=1)

    # Subplot 1: Speed Trace
    fig.add_trace(go.Scatter(
        x=df_chart["timestamp"],
        y=df_chart["velocita_plot_y"],
        text=df_chart["speed_label"],
        textposition="bottom center",
        textfont=dict(family="Arial, sans-serif", size=9.5 if span_h >= 720 else 10.0, color="#0f172a"),
        customdata=np.stack((df_chart["velocita_bft"], df_chart["velocita_knots"], df_chart["direzione_deg"]), axis=-1),
        mode="lines+markers+text",
        name="Wind Speed (Avg)",
        line=dict(color="#0f172a", width=1.8 if span_h >= 720 else 2.2),
        marker=dict(symbol="circle", size=3.0 if span_h >= 720 else (3.5 if span_h >= 72 else 4.0), color="#0f172a"),
        hovertemplate="<b>Speed:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<br><b>Dir:</b> %{customdata[2]:.0f}°<extra></extra>"
    ), row=1, col=1)

    # Exact Stemmed Mini-Arrows (Subplot 1)
    mini_arrow_len = 18
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
            yshift=-24,
            ax=-dx,
            ay=dy,
            axref="pixel",
            ayref="pixel",
            showarrow=True,
            arrowhead=2,
            arrowsize=1.35,
            arrowwidth=1.3,
            arrowcolor="#0f172a",
            opacity=0.95
        )

    # Subplot 2: Direction Scatter
    fig.add_trace(go.Scatter(
        x=df_chart["timestamp"],
        y=df_chart["direzione_deg"],
        mode="markers",
        name="Direction",
        marker=dict(symbol="circle", size=2.5 if span_h >= 720 else (3.0 if span_h >= 72 else 3.5), color="#64748b"),
        customdata=df_chart[["direzione_cardinal", "velocita_knots", "velocita_bft"]],
        hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[2]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=2, col=1)

    # Subplot 2: Adaptive Vector Arrows
    target_arrow_count = 14 if span_h >= 720 else (18 if span_h >= 72 else 25)
    steady_step = max(3, len(df_chart) // target_arrow_count)
    selected_indices = []
    if not df_chart.empty:
        selected_indices.append(0)
        last_idx = 0
        last_deg = df_chart.loc[0, "direzione_deg"]

        for i in range(1, len(df_chart)):
            curr_deg = df_chart.loc[i, "direzione_deg"]
            if pd.isna(curr_deg):
                continue
            delta_deg = abs((curr_deg - last_deg + 180) % 360 - 180)
            points_since_last = i - last_idx

            angle_sens = 45.0 if span_h >= 720 else (35.0 if span_h >= 72 else 20.0)
            if delta_deg > angle_sens or points_since_last >= steady_step:
                selected_indices.append(i)
                last_idx = i
                last_deg = curr_deg

    df_sub = df_chart.iloc[selected_indices]
    arrow_length_px = 36

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
            arrowsize=2,
            arrowwidth=1.5,
            arrowcolor=arrow_color,
            opacity=0.9
        )

    # Subplot 3: Temperature
    if has_temp:
        is_day = df_chart["timestamp"].dt.hour.between(6, 18)
        temp_day = df_chart["temperatura_c"].where(is_day, np.nan)
        temp_night = df_chart["temperatura_c"].where(~is_day, np.nan)

        fig.add_trace(go.Scatter(
            x=df_chart["timestamp"],
            y=temp_day,
            mode="lines+markers",
            name="Temp (Day: 06-19h)",
            line=dict(color="#eab308", width=1.8 if span_h >= 720 else 2.2),
            marker=dict(size=2.5 if span_h >= 720 else (3.5 if span_h >= 72 else 4), color="#eab308"),
            hovertemplate="<b>Temp (Day):</b> %{y:.1f} °C<extra></extra>"
        ), row=3, col=1)

        if not daytime_only:
            fig.add_trace(go.Scatter(
                x=df_chart["timestamp"],
                y=temp_night,
                mode="lines+markers",
                name="Temp (Night: 19-06h)",
                line=dict(color="#1e3a8a", width=1.8 if span_h >= 720 else 2.2),
                marker=dict(size=2.5 if span_h >= 720 else (3.5 if span_h >= 72 else 4), color="#1e3a8a"),
                hovertemplate="<b>Temp (Night):</b> %{y:.1f} °C<extra></extra>"
            ), row=3, col=1)

        fig.update_yaxes(
            title_text="<b>°C</b>",
            title_font=dict(color="#0f172a", size=12),
            tickfont=dict(color="#0f172a", size=11),
            fixedrange=True,
            gridcolor="#cbd5e1",
            showline=False,
            row=3, col=1
        )

    # Axis Calibrations
    bft_ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    bft_stretched_vals = [bft_to_stretched(b) for b in bft_ticks]
    bft_labels = [
        "0 Bft", "1 Bft", "2 Bft", "3 Bft (Gentle)", "4 Bft (Moderate)",
        "5 Bft (Fresh)", "6 Bft (Strong)", "7 Bft (Near Gale)", "8 Bft (Gale)", "9 Bft (Storm)"
    ]

    fig.update_yaxes(
        title_text="<b>Beaufort Force (Stretched)</b>",
        title_font=dict(color="#0f172a", size=12),
        range=[0, top_y_limit],
        tickvals=bft_stretched_vals,
        ticktext=bft_labels,
        tickfont=dict(color="#0f172a", size=11),
        fixedrange=True,
        gridcolor="#cbd5e1",
        zerolinecolor="#cbd5e1",
        showline=False,
        row=1, col=1
    )

    fig.update_yaxes(
        title_text="<b>Direction</b>",
        title_font=dict(color="#0f172a", size=12),
        range=[-35, 395],
        tickvals=[0, 90, 180, 270, 360],
        ticktext=["N (0°)", "E (90°)", "S (180°)", "W (270°)", "N (360°)"],
        tickfont=dict(color="#0f172a", size=11),
        fixedrange=True,
        gridcolor="#cbd5e1",
        showline=False,
        row=2, col=1
    )

    fig.update_xaxes(
        range=[v_start, v_end],
        gridcolor="#cbd5e1",
        showgrid=True,
        showline=False
    )

    fig.update_layout(
        height=780 if has_temp else 600,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        hovermode="x unified",
        dragmode="pan",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.9)"
        ),
        margin=dict(l=35, r=20, t=50, b=30)
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "scrollZoom": True,
            "displayModeBar": True,
            "displaylogo": False,
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
