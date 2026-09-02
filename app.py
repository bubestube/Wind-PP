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

# Continuous Beaufort Color Scale for Area Fills (0 to 8+ Bft)
WIND_COLORSCALE_GUST = [
[0.00, "rgba(255, 255, 255, 0.25)"],  # 0-1 Bft: Calm / Light
@@ -176,6 +184,22 @@
font-weight: 600 !important;
margin: 0 !important;
}

    /* 4. Month Reading Pill above Slider */
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
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
        margin-bottom: 2px;
    }
</style>
""", unsafe_allow_html=True)

@@ -273,7 +297,7 @@
with ctrl_col3:
st.session_state.window_span_hours = st.selectbox(
"Window Width:",
            options=[6, 12, 24, 72, 168],
            options=[6, 12, 24, 72, 168, 720],
index=0,
format_func=lambda h: f"{h} Hours" if h < 24 else f"{h//24} Day{'s' if h > 24 else ''}"
)
@@ -291,6 +315,21 @@
st.session_state.window_end_time = t_global_max.to_pydatetime()
st.rerun()

    # Active Month Pill
    cur_end_preview = pd.to_datetime(st.session_state.window_end_time)
    cur_start_preview = cur_end_preview - pd.Timedelta(hours=st.session_state.window_span_hours)
    if cur_start_preview.strftime("%B %Y") == cur_end_preview.strftime("%B %Y"):
        active_month_str = cur_end_preview.strftime("%B %Y")
    elif cur_start_preview.year == cur_end_preview.year:
        active_month_str = f"{cur_start_preview.strftime('%B')} – {cur_end_preview.strftime('%B %Y')}"
    else:
        active_month_str = f"{cur_start_preview.strftime('%B %Y')} – {cur_end_preview.strftime('%B %Y')}"

    st.markdown(
        f'<div class="slider-month-pill">📅 <span>{active_month_str}</span></div>',
        unsafe_allow_html=True
    )

# High-precision Timeline Slider for Continuous Scrolling
min_slider = (t_global_min + pd.Timedelta(hours=st.session_state.window_span_hours)).to_pydatetime()
max_slider = t_global_max.to_pydatetime()
@@ -319,7 +358,32 @@
st.warning("No records in selected window.")
df_slice = df_all.tail(20).copy()

    # Calculations on the micro-slice only (<50-60 points)
    # --- Adaptive Density Reduction for Long Intervals (3 Days, 7 Days, 30 Days) ---
    span_h = st.session_state.window_span_hours
    if span_h >= 720:          # 30 Days: 2-hour buckets
        resample_rule = "2h"
        bar_width_ms = 2 * 60 * 60 * 1000
    elif span_h >= 168:        # 7 Days: 30-minute buckets
        resample_rule = "30min"
        bar_width_ms = 30 * 60 * 1000
    elif span_h >= 72:         # 3 Days: 15-minute buckets
        resample_rule = "15min"
        bar_width_ms = 15 * 60 * 1000
    else:                      # <= 1 Day: Raw native resolution
        resample_rule = None
        bar_width_ms = 2 * 60 * 1000

    if resample_rule is not None and not df_slice.empty:
        df_resampled = df_slice.set_index("timestamp").resample(resample_rule).agg({
            "velocita_knots": "mean",
            "raffica_knots": "max",
            "direzione_deg": "mean",
            "temperatura_c": "mean"
        }).dropna(subset=["velocita_knots"]).reset_index()

        df_resampled["direzione_cardinal"] = df_resampled["direzione_deg"].apply(deg_to_cardinal)
        df_slice = df_resampled

df_slice["velocita_bft"] = knots_to_bft(df_slice["velocita_knots"])
df_slice["raffica_bft"] = knots_to_bft(df_slice["raffica_knots"])
df_slice["velocita_plot_y"] = bft_to_stretched(df_slice["velocita_bft"])
@@ -331,7 +395,14 @@
# Gap Disconnectors
df_plot = df_slice.sort_values("timestamp").reset_index(drop=True)
time_diffs = df_plot["timestamp"].diff()
    gap_indices = df_plot[time_diffs > pd.Timedelta(minutes=45)].index
    if span_h >= 720:
        gap_threshold = pd.Timedelta(hours=8)
    elif span_h >= 72:
        gap_threshold = pd.Timedelta(hours=2)
    else:
        gap_threshold = pd.Timedelta(minutes=45)

    gap_indices = df_plot[time_diffs > gap_threshold].index

if len(gap_indices) > 0:
nan_rows = []
@@ -353,7 +424,7 @@
else:
df_plot_lines = df_plot.copy()

    # Precise Dynamic Labels & Arrow Anchors
    # Adaptive Text Labels & Vector Arrow Anchors
speed_labels = [""] * len(df_plot_lines)
gust_labels = [""] * len(df_plot_lines)
labeled_speed_points = []
@@ -383,6 +454,24 @@
y_arr = df_plot_lines["velocita_plot_y"].to_numpy()
t_arr = df_plot_lines["timestamp"].to_numpy()

        # Step limits scale dynamically with duration to prevent overlap
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
curr_v = v_arr[idx]
curr_d = d_arr[idx]
@@ -391,7 +480,7 @@
delta_s = abs(curr_v - last_s_val)
pts_since_s = idx - last_s_idx

            if (delta_s >= 1.0 and pts_since_s >= 2) or pts_since_s >= 8:
            if (delta_s >= delta_threshold and pts_since_s >= min_pts_step) or pts_since_s >= max_pts_step:
speed_labels[idx] = f"{curr_v:.1f}"
labeled_speed_points.append({
"timestamp": t_arr[idx],
@@ -404,29 +493,31 @@
if pd.notnull(curr_g):
delta_g = abs(curr_g - last_g_val)
pts_since_g = idx - last_g_idx
                if (delta_g >= 1.0 and pts_since_g >= 2) or pts_since_g >= 8:
                if (delta_g >= delta_threshold and pts_since_g >= min_pts_step) or pts_since_g >= max_pts_step:
gust_labels[idx] = f"{curr_g:.1f}"
last_g_val = curr_g
last_g_idx = idx

df_plot_lines["speed_label"] = speed_labels
df_plot_lines["gust_label"] = gust_labels

    # Micro-slice fast gradient interpolation
    fill_segments = []
    seg_start = 0
    gap_pos = list(gap_indices) + [len(df_plot)]
    for g_pos in gap_pos:
        seg = df_plot.iloc[seg_start:g_pos]
        if len(seg) >= 2:
            seg_resampled = seg.set_index("timestamp")[["velocita_plot_y", "raffica_plot_y", "velocita_bft", "raffica_bft"]].resample("2min").interpolate(method="time").reset_index()
            fill_segments.append(seg_resampled)
        elif len(seg) == 1:
            fill_segments.append(seg[["timestamp", "velocita_plot_y", "raffica_plot_y", "velocita_bft", "raffica_bft"]])
        seg_start = g_pos

    df_gradient_fill = pd.concat(fill_segments, ignore_index=True) if fill_segments else df_plot.copy()
    bar_width_ms = 2 * 60 * 1000
    # Fast Gradient Fill Interpolation
    if resample_rule is not None:
        df_gradient_fill = df_plot.copy()
    else:
        fill_segments = []
        seg_start = 0
        gap_pos = list(gap_indices) + [len(df_plot)]
        for g_pos in gap_pos:
            seg = df_plot.iloc[seg_start:g_pos]
            if len(seg) >= 2:
                seg_resampled = seg.set_index("timestamp")[["velocita_plot_y", "raffica_plot_y", "velocita_bft", "raffica_bft"]].resample("2min").interpolate(method="time").reset_index()
                fill_segments.append(seg_resampled)
            elif len(seg) == 1:
                fill_segments.append(seg[["timestamp", "velocita_plot_y", "raffica_plot_y", "velocita_bft", "raffica_bft"]])
            seg_start = g_pos

        df_gradient_fill = pd.concat(fill_segments, ignore_index=True) if fill_segments else df_plot.copy()

# 5. Multi-Panel Subplots
fig = make_subplots(
@@ -482,13 +573,13 @@
y=df_plot_lines["raffica_plot_y"],
text=df_plot_lines["gust_label"],
textposition="top center",
        textfont=dict(family="Arial, sans-serif", size=10.0, color="#b91c1c"),
        textfont=dict(family="Arial, sans-serif", size=9.5 if span_h >= 720 else 10.0, color="#b91c1c"),
customdata=np.stack((df_plot_lines["raffica_bft"], df_plot_lines["raffica_knots"]), axis=-1),
mode="lines+markers+text",
name="Gust (Raffica)",
connectgaps=False,
        line=dict(color="#0f172a", width=1.6, dash="dot"),
        marker=dict(symbol="circle", size=4.0, color="#0f172a"),
        line=dict(color="#0f172a", width=1.4 if span_h >= 720 else 1.6, dash="dot"),
        marker=dict(symbol="circle", size=3.0 if span_h >= 720 else (3.5 if span_h >= 72 else 4.0), color="#0f172a"),
hovertemplate="<b>Gust:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
), row=1, col=1)

@@ -498,13 +589,13 @@
y=df_plot_lines["velocita_plot_y"],
text=df_plot_lines["speed_label"],
textposition="bottom center",
        textfont=dict(family="Arial, sans-serif", size=10.0, color="#0f172a"),
        textfont=dict(family="Arial, sans-serif", size=9.5 if span_h >= 720 else 10.0, color="#0f172a"),
customdata=np.stack((df_plot_lines["velocita_bft"], df_plot_lines["velocita_knots"], df_plot_lines["direzione_deg"]), axis=-1),
mode="lines+markers+text",
name="Wind Speed (Avg)",
connectgaps=False,
        line=dict(color="#0f172a", width=2.2),
        marker=dict(size=4.0, color="#0f172a"),
        line=dict(color="#0f172a", width=1.8 if span_h >= 720 else 2.2),
        marker=dict(size=3.0 if span_h >= 720 else (3.5 if span_h >= 72 else 4.0), color="#0f172a"),
hovertemplate="<b>Speed:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<br><b>Dir:</b> %{customdata[2]:.0f}°<extra></extra>"
), row=1, col=1)

@@ -544,16 +635,17 @@
mode="markers",
name="Direction",
connectgaps=False,
        marker=dict(symbol="circle", size=3.5, color="#64748b"),
        marker=dict(symbol="circle", size=2.5 if span_h >= 720 else (3.0 if span_h >= 72 else 3.5), color="#64748b"),
customdata=df_plot_lines[["direzione_cardinal", "velocita_knots", "velocita_bft"]],
hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[2]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
), row=2, col=1)

    # Subplot 2: Rotating Vector Arrows on Active Slice (Shorter stem)
    # Subplot 2: Direction Arrows Throttled to Match Horizon
df_for_arrows = df_slice.sort_values("timestamp").reset_index(drop=True)
df_for_arrows["arrow_angle"] = (df_for_arrows["direzione_deg"].fillna(0) + 180) % 360

    steady_step = max(3, len(df_for_arrows) // 25)
    target_arrow_count = 14 if span_h >= 720 else (18 if span_h >= 72 else 25)
    steady_step = max(3, len(df_for_arrows) // target_arrow_count)
selected_indices = []
if not df_for_arrows.empty:
selected_indices.append(0)
@@ -567,13 +659,14 @@
delta_deg = abs((curr_deg - last_deg + 180) % 360 - 180)
points_since_last = i - last_idx

            if delta_deg > 20.0 or points_since_last >= steady_step:
            angle_sens = 45.0 if span_h >= 720 else (35.0 if span_h >= 72 else 20.0)
            if delta_deg > angle_sens or points_since_last >= steady_step:
selected_indices.append(i)
last_idx = i
last_deg = curr_deg

df_sub = df_for_arrows.iloc[selected_indices]
    arrow_length_px = 36  # Shortened from 60px
    arrow_length_px = 36

for _, row_data in df_sub.iterrows():
angle_deg = row_data["arrow_angle"]
@@ -617,8 +710,8 @@
mode="lines+markers",
name="Temp (Day: 06-19h)",
connectgaps=False,
            line=dict(color="#eab308", width=2.2),
            marker=dict(size=4, color="#eab308", line=dict(color="#ca8a04", width=1)),
            line=dict(color="#eab308", width=1.8 if span_h >= 720 else 2.2),
            marker=dict(size=2.5 if span_h >= 720 else (3.5 if span_h >= 72 else 4), color="#eab308", line=dict(color="#ca8a04", width=1)),
hovertemplate="<b>Temp (Day):</b> %{y:.1f} °C<extra></extra>"
), row=3, col=1)

@@ -629,8 +722,8 @@
mode="lines+markers",
name="Temp (Night: 19-06h)",
connectgaps=False,
                line=dict(color="#1e3a8a", width=2.2),
                marker=dict(size=4, color="#1e3a8a", line=dict(color="#0f172a", width=1)),
                line=dict(color="#1e3a8a", width=1.8 if span_h >= 720 else 2.2),
                marker=dict(size=2.5 if span_h >= 720 else (3.5 if span_h >= 72 else 4), color="#1e3a8a", line=dict(color="#0f172a", width=1)),
hovertemplate="<b>Temp (Night):</b> %{y:.1f} °C<extra></extra>"
), row=3, col=1)
