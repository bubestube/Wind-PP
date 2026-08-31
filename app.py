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

# True Meteorological Wind Arrow
def deg_to_wind_arrow(deg):
    if pd.isna(deg):
        return ""
    arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]
    idx = int(((float(deg) % 360) + 22.5) // 45) % 8
    return arrows[idx]

# Continuous Beaufort Color Scale for Area Fills (0 to 8+ Bft)
WIND_COLORSCALE_GUST = [
    [0.00, "rgba(255, 255, 255, 0.25)"],  # 0-1 Bft: Calm / Light
    [0.22, "rgba(56, 189, 248, 0.30)"],   # 2-3 Bft: Light/Gentle Breeze
    [0.40, "rgba(37, 99, 235, 0.35)"],    # 4 Bft: Moderate Breeze
    [0.55, "rgba(34, 197, 94, 0.40)"],    # 5 Bft: Fresh Breeze
    [0.70, "rgba(234, 179, 8, 0.45)"],    # 6 Bft: Strong Breeze
    [0.85, "rgba(168, 85, 247, 0.50)"],   # 7 Bft: Near Gale
    [1.00, "rgba(239, 68, 68, 0.55)"]     # 8+ Bft: Gale / Storm
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
    </style>
""", unsafe_allow_html=True)

st.title("🪁 Porto Pollo (Sardinia) – Live Wind Station")
st.caption("Gradient-shaded Beaufort monitor (*Default 6h view with infinite backward scrolling*).")

# 1. Cached Data Loader
@st.cache_data(ttl=60, show_spinner=False)
def load_all_records(csv_path):
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path, on_bad_lines="skip")
    if df.empty or "timestamp" not in df.columns:
        return None
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    df = df[df["timestamp"] >= "2026-08-27 13:11:00"].reset_index(drop=True)
    if df.empty:
        return None

    df["velocita_bft"] = knots_to_bft(df["velocita_knots"])
    df["raffica_bft"] = knots_to_bft(df["raffica_knots"])
    df["velocita_plot_y"] = bft_to_stretched(df["velocita_bft"])
    df["raffica_plot_y"] = bft_to_stretched(df["raffica_bft"])
    df["arrow_angle"] = (df["direzione_deg"].fillna(0) + 180) % 360
    return df

df = load_all_records(CSV_FILE)

if df is not None and not df.empty:
    latest = df.iloc[-1]
    latest_bft = latest['velocita_bft']

    # 2. KPI Cards
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

    # 3. Viewport Presets & Daytime Filter
    col_preset, col_daytime = st.columns([3, 1])
    with col_preset:
        time_preset = st.radio(
            "Initial Viewport Range:",
            options=["Last 6 Hours (Default)", "Last 24 Hours", "Last 3 Days", "Last 7 Days", "Fit All History"],
            index=0,
            horizontal=True
        )
    with col_daytime:
        st.write("")
        daytime_only = st.checkbox("☀️ Daytime Only (06:00 – 19:00)", value=False)

    df_filtered = df.copy()
    if daytime_only:
        df_filtered = df_filtered[df_filtered["timestamp"].dt.hour.between(6, 18)].copy()

    if df_filtered.empty:
        st.warning("No records found.")
        df_filtered = df.copy()

    has_temp = "temperatura_c" in df_filtered.columns and df_filtered["temperatura_c"].notnull().any()

    # Gap Disconnectors
    df_plot = df_filtered.copy().sort_values("timestamp").reset_index(drop=True)
    time_diffs = df_plot["timestamp"].diff()
    gap_indices = df_plot[time_diffs > pd.Timedelta(minutes=45)].index

    if len(gap_indices) > 0:
        nan_rows = []
        for idx in gap_indices:
            prev_time = df_plot.loc[idx - 1, "timestamp"]
            nan_rows.append(pd.DataFrame([{
                "timestamp": prev_time + pd.Timedelta(seconds=1),
                "velocita_knots": np.nan,
                "raffica_knots": np.nan,
                "velocita_bft": np.nan,
                "raffica_bft": np.nan,
                "velocita_plot_y": np.nan,
                "raffica_plot_y": np.nan,
                "temperatura_c": np.nan,
                "direzione_deg": np.nan,
                "direzione_cardinal": None
            }]))
        df_plot_lines = pd.concat([df_plot] + nan_rows).sort_values("timestamp").reset_index(drop=True)
    else:
        df_plot_lines = df_plot.copy()

    # Dynamic Labels & Wind Direction Vectors (Bigger & Bolder Arrows)
    speed_labels = [""] * len(df_plot_lines)
    gust_labels = [""] * len(df_plot_lines)

    valid_mask = df_plot_lines["velocita_knots"].notnull()
    valid_indices = df_plot_lines.index[valid_mask].tolist()

    if valid_indices:
        f_idx = valid_indices[0]
        v0 = df_plot_lines.loc[f_idx, 'velocita_knots']
        d0 = df_plot_lines.loc[f_idx, 'direzione_deg']
        a0 = deg_to_wind_arrow(d0)
        speed_labels[f_idx] = f"{v0:.1f}<br><b style='font-size:15px; line-height:1.2;'>{a0}</b>"

        last_s_val = v0
        last_s_idx = f_idx
        last_g_val = df_plot_lines.loc[f_idx, 'raffica_knots'] if pd.notnull(df_plot_lines.loc[f_idx, 'raffica_knots']) else -999.0
        last_g_idx = f_idx

        v_arr = df_plot_lines["velocita_knots"].to_numpy()
        r_arr = df_plot_lines["raffica_knots"].to_numpy()
        d_arr = df_plot_lines["direzione_deg"].to_numpy()

        for idx in valid_indices[1:]:
            curr_v = v_arr[idx]
            curr_d = d_arr[idx]
            curr_g = r_arr[idx]

            delta_s = abs(curr_v - last_s_val)
            pts_since_s = idx - last_s_idx

            if (delta_s >= 1.0 and pts_since_s >= 2) or pts_since_s >= 8:
                arrow = deg_to_wind_arrow(curr_d)
                # Bolder and larger (15px) direction arrow beneath wind speed
                speed_labels[idx] = f"{curr_v:.1f}<br><b style='font-size:15px; line-height:1.2;'>{arrow}</b>"
                last_s_val = curr_v
                last_s_idx = idx

            if pd.notnull(curr_g):
                delta_g = abs(curr_g - last_g_val)
                pts_since_g = idx - last_g_idx
                if (delta_g >= 1.0 and pts_since_g >= 2) or pts_since_g >= 8:
                    gust_labels[idx] = f"{curr_g:.1f}"
                    last_g_val = curr_g
                    last_g_idx = idx

    df_plot_lines["speed_label"] = speed_labels
    df_plot_lines["gust_label"] = gust_labels

    # --- Smooth Gradient Resampling across Full Timeline ---
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
    bar_width_ms = 2 * 60 * 1000  # 2 minute gradient bar resolution

    # 4. Build Multi-Panel Subplots
    fig = make_subplots(
        rows=3 if has_temp else 2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.035,
        subplot_titles=(
            "<b>Wind speed and gusts (Stretched Beaufort Scale)</b>",
            "<b>Wind direction</b>",
            "<b>Temperature (°C) – 🟡 Daytime (06-19h) | 🔵 Nighttime (19-06h)</b>" if has_temp else None
        ),
        row_heights=[0.54, 0.28, 0.18] if has_temp else [0.65, 0.35]
    )

    # Subplot 1: Gust Gradient Fill Area
    fig.add_trace(go.Bar(
        x=df_gradient_fill["timestamp"],
        y=df_gradient_fill["raffica_plot_y"],
        marker=dict(
            color=df_gradient_fill["raffica_bft"],
            colorscale=WIND_COLORSCALE_GUST,
            cmin=0,
            cmax=8,
            line=dict(width=0)
        ),
        width=bar_width_ms,
        hoverinfo="skip",
        showlegend=False,
        name="Gust Gradient Fill"
    ), row=1, col=1)

    # Subplot 1: Sustained Speed Gradient Fill Area
    fig.add_trace(go.Bar(
        x=df_gradient_fill["timestamp"],
        y=df_gradient_fill["velocita_plot_y"],
        marker=dict(
            color=df_gradient_fill["velocita_bft"],
            colorscale=WIND_COLORSCALE_SPEED,
            cmin=0,
            cmax=8,
            line=dict(width=0)
        ),
        width=bar_width_ms,
        hoverinfo="skip",
        showlegend=False,
        name="Speed Gradient Fill"
    ), row=1, col=1)

    # Subplot 1: Gust Trace
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["raffica_plot_y"],
        text=df_plot_lines["gust_label"],
        textposition="top center",
        textfont=dict(family="Arial, sans-serif", size=10.0, color="#b91c1c"),
        customdata=np.stack((df_plot_lines["raffica_bft"], df_plot_lines["raffica_knots"]), axis=-1),
        mode="lines+markers+text",
        name="Gust (Raffica)",
        connectgaps=False,
        line=dict(color="#0f172a", width=1.6, dash="dot"),
        marker=dict(symbol="circle", size=4.0, color="#0f172a"),
        hovertemplate="<b>Gust:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=1, col=1)

    # Subplot 1: Sustained Speed Trace with Number & Direction Arrow Below
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["velocita_plot_y"],
        text=df_plot_lines["speed_label"],
        textposition="bottom center",
        textfont=dict(family="Arial, sans-serif", size=10.0, color="#0f172a"),
        customdata=np.stack((df_plot_lines["velocita_bft"], df_plot_lines["velocita_knots"], df_plot_lines["direzione_deg"]), axis=-1),
        mode="lines+markers+text",
        name="Wind Speed (Avg)",
        connectgaps=False,
        line=dict(color="#0f172a", width=2.2),
        marker=dict(size=4.0, color="#0f172a"),
        hovertemplate="<b>Speed:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<br><b>Dir:</b> %{customdata[2]:.0f}°<extra></extra>"
    ), row=1, col=1)

    # Subplot 2: Direction Trace
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["direzione_deg"],
        mode="markers",
        name="Direction",
        connectgaps=False,
        marker=dict(symbol="circle", size=3.5, color="#64748b"),
        customdata=df_plot_lines[["direzione_cardinal", "velocita_knots", "velocita_bft"]],
        hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[2]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=2, col=1)

    # --- SUBPLOT 2: Restored Rotating Vector Wind Arrows (Green >= 18kts, Red < 18kts) ---
    df_for_arrows = df_filtered.copy().sort_values("timestamp").reset_index(drop=True)
    df_for_arrows["arrow_angle"] = (df_for_arrows["direzione_deg"].fillna(0) + 180) % 360

    steady_step = max(3, len(df_for_arrows) // 40)
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

            if delta_deg > 20.0 or points_since_last >= steady_step:
                selected_indices.append(i)
                last_idx = i
                last_deg = curr_deg

    df_sub = df_for_arrows.iloc[selected_indices]
    arrow_length_px = 44

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
            arrowsize=1.0,
            arrowwidth=1.8,
            arrowcolor=arrow_color,
            opacity=0.9
        )

    # Subplot 3: Temperature
    if has_temp:
        is_day = df_plot_lines["timestamp"].dt.hour.between(6, 18)
        temp_day = df_plot_lines["temperatura_c"].where(is_day, np.nan)
        temp_night = df_plot_lines["temperatura_c"].where(~is_day, np.nan)

        fig.add_trace(go.Scatter(
            x=df_plot_lines["timestamp"],
            y=temp_day,
            mode="lines+markers",
            name="Temp (Day: 06-19h)",
            connectgaps=False,
            line=dict(color="#eab308", width=2.2),
            marker=dict(size=4, color="#eab308", line=dict(color="#ca8a04", width=1)),
            hovertemplate="<b>Temp (Day):</b> %{y:.1f} °C<extra></extra>"
        ), row=3, col=1)

        if not daytime_only:
            fig.add_trace(go.Scatter(
                x=df_plot_lines["timestamp"],
                y=temp_night,
                mode="lines+markers",
                name="Temp (Night: 19-06h)",
                connectgaps=False,
                line=dict(color="#1e3a8a", width=2.2),
                marker=dict(size=4, color="#1e3a8a", line=dict(color="#0f172a", width=1)),
                hovertemplate="<b>Temp (Night):</b> %{y:.1f} °C<extra></extra>"
            ), row=3, col=1)

        fig.update_yaxes(title_text="°C", row=3, col=1, gridcolor="#e2e8f0", fixedrange=True)

    # Vertical Night Shading
    if not daytime_only and not df_plot_lines.empty:
        t_min_full = df_plot_lines["timestamp"].min()
        t_max_full = df_plot_lines["timestamp"].max()
        curr_day = t_min_full.floor("D")
        while curr_day <= t_max_full:
            night_start = curr_day + pd.Timedelta(hours=19)
            night_end = curr_day + pd.Timedelta(days=1, hours=6)
            if night_end >= t_min_full and night_start <= t_max_full:
                fig.add_vrect(
                    x0=max(night_start, t_min_full),
                    x1=min(night_end, t_max_full),
                    fillcolor="rgba(15, 23, 42, 0.04)",
                    layer="below",
                    line_width=0
                )
            curr_day += pd.Timedelta(days=1)

    # Axis Calibrations
    bft_ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    bft_stretched_vals = [bft_to_stretched(b) for b in bft_ticks]
    bft_labels = [
        "0 Bft", "1 Bft", "2 Bft", "3 Bft (Gentle)", "4 Bft (Moderate)",
        "5 Bft (Fresh)", "6 Bft (Strong)", "7 Bft (Near Gale)", "8 Bft (Gale)", "9 Bft (Storm)"
    ]

    max_observed_y = df_plot_lines["raffica_plot_y"].dropna().max() if not df_plot_lines["raffica_plot_y"].dropna().empty else bft_to_stretched(7.5)
    top_y_limit = max(bft_to_stretched(7.5), max_observed_y * 1.14)

    fig.update_yaxes(
        title_text="<b>Beaufort Force (Stretched)</b>",
        range=[0, top_y_limit],
        tickvals=bft_stretched_vals,
        ticktext=bft_labels,
        row=1, col=1,
        gridcolor="#e2e8f0",
        zerolinecolor="#cbd5e1",
        fixedrange=True
    )

    fig.update_yaxes(
        title_text="Direction",
        range=[-35, 395],
        tickvals=[0, 90, 180, 270, 360],
        ticktext=["N (0°)", "E (90°)", "S (180°)", "W (270°)", "N (360°)"],
        row=2, col=1,
        gridcolor="#e2e8f0",
        fixedrange=True
    )

    # 5. Default 6h Initial Viewport Window
    t_end_view = df_plot_lines["timestamp"].max()
    t_start_data = df_plot_lines["timestamp"].min()

    if time_preset == "Last 6 Hours (Default)":
        t_start_view = max(t_start_data, t_end_view - pd.Timedelta(hours=6))
    elif time_preset == "Last 24 Hours":
        t_start_view = max(t_start_data, t_end_view - pd.Timedelta(hours=24))
    elif time_preset == "Last 3 Days":
        t_start_view = max(t_start_data, t_end_view - pd.Timedelta(days=3))
    elif time_preset == "Last 7 Days":
        t_start_view = max(t_start_data, t_end_view - pd.Timedelta(days=7))
    else:
        t_start_view = t_start_data

    fig.update_xaxes(
        gridcolor="#e2e8f0",
        showgrid=True,
        range=[t_start_view, t_end_view]
    )

    fig.update_layout(
        height=780 if has_temp else 600,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        bargap=0,
        barmode="overlay",
        font=dict(color="#1e293b", family="Arial, sans-serif"),
        dragmode="pan",
        hovermode="x unified",
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

    # 6. Render Chart
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

    with st.expander("📋 View Full Data Log"):
        st.dataframe(
            df_filtered.sort_values("timestamp", ascending=False),
            use_container_width=True
        )
else:
    st.info("No data file found yet.")
