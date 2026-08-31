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

# --- Fast Vectorized Helpers ---
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

# True Meteorological Wind Arrow (Points to direction of airflow)
def deg_to_wind_arrow(deg):
    if pd.isna(deg):
        return ""
    # 0° (N) -> blows S (⬇), 90° (E) -> blows W (⬅), etc.
    arrows = ["⬇", "⬋", "⬅", "⬉", "⬆", "⬈", "➡", "⬊"]
    idx = int(((float(deg) % 360) + 22.5) // 45) % 8
    return arrows[idx]

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

# 1. Cached Data Loader
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
        if df.empty:
            return None

        df["velocita_bft"] = knots_to_bft(df["velocita_knots"])
        df["raffica_bft"] = knots_to_bft(df["raffica_knots"])
        df["velocita_plot_y"] = bft_to_stretched(df["velocita_bft"])
        df["raffica_plot_y"] = bft_to_stretched(df["raffica_bft"])
        return df
    except Exception as e:
        st.error(f"Error loading CSV data: {e}")
        return None

df_raw = load_all_records(CSV_FILE)

if df_raw is not None and not df_raw.empty:
    latest = df_raw.iloc[-1]
    latest_bft = latest['velocita_bft']

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

    # 3. Viewport Presets
    col_preset, col_daytime = st.columns([3, 1])
    with col_preset:
        time_preset = st.radio(
            "Time Range Window:",
            options=["Last 6 Hours (Default)", "Last 24 Hours", "Last 3 Days", "Last 7 Days", "All History"],
            index=0,
            horizontal=True
        )
    with col_daytime:
        st.write("")
        daytime_only = st.checkbox("☀️ Daytime Only (06:00 – 19:00)", value=False)

    df_filtered = df_raw.copy()
    if daytime_only:
        df_filtered = df_filtered[df_filtered["timestamp"].dt.hour.between(6, 18)].copy()

    # Viewport Bounds Calculation
    t_max = df_filtered["timestamp"].max()
    if time_preset == "Last 6 Hours (Default)":
        t_min = t_max - pd.Timedelta(hours=6)
    elif time_preset == "Last 24 Hours":
        t_min = t_max - pd.Timedelta(hours=24)
    elif time_preset == "Last 3 Days":
        t_min = t_max - pd.Timedelta(days=3)
    elif time_preset == "Last 7 Days":
        t_min = t_max - pd.Timedelta(days=7)
    else:
        t_min = df_filtered["timestamp"].min()

    # Slice strictly to the selected range
    df_slice = df_filtered[(df_filtered["timestamp"] >= t_min) & (df_filtered["timestamp"] <= t_max)].copy()
    if df_slice.empty:
        df_slice = df_filtered.tail(30).copy()

    has_temp = "temperatura_c" in df_slice.columns and df_slice["temperatura_c"].notnull().any()

    # Gap Disconnectors (Connectgaps safety)
    df_plot = df_slice.sort_values("timestamp").reset_index(drop=True)
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

    # In-Trace Numbers and Vectors (Zero layout annotation overhead)
    speed_labels = [""] * len(df_plot_lines)
    gust_labels = [""] * len(df_plot_lines)
    dir_arrows = [""] * len(df_plot_lines)

    valid_mask = df_plot_lines["velocita_knots"].notnull()
    valid_indices = df_plot_lines.index[valid_mask].tolist()

    if valid_indices:
        step_stride = max(2, len(valid_indices) // 20)
        for i, idx in enumerate(valid_indices):
            if i % step_stride == 0 or i == len(valid_indices) - 1:
                v = df_plot_lines.loc[idx, "velocita_knots"]
                d = df_plot_lines.loc[idx, "direzione_deg"]
                arrow = deg_to_wind_arrow(d)
                
                speed_labels[idx] = f"{v:.1f}<br><span style='font-size:13px;'>{arrow}</span>"
                dir_arrows[idx] = f"<span style='font-size:14px; font-weight:bold;'>{arrow}</span>"

                if pd.notnull(df_plot_lines.loc[idx, "raffica_knots"]):
                    gust_labels[idx] = f"{df_plot_lines.loc[idx, 'raffica_knots']:.1f}"

    df_plot_lines["speed_label"] = speed_labels
    df_plot_lines["gust_label"] = gust_labels
    df_plot_lines["dir_arrow"] = dir_arrows

    # 4. Multi-Panel Subplots
    fig = make_subplots(
        rows=3 if has_temp else 2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.04,
        subplot_titles=(
            "<b>Wind speed and gusts (Stretched Beaufort Scale)</b>",
            "<b>Wind direction & Vector Flow</b>",
            "<b>Temperature (°C) – 🟡 Daytime (06-19h) | 🔵 Nighttime (19-06h)</b>" if has_temp else None
        ),
        row_heights=[0.54, 0.28, 0.18] if has_temp else [0.65, 0.35]
    )

    # Subplot 1: Gust Shaded Area
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["raffica_plot_y"],
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(239, 68, 68, 0.16)",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
        connectgaps=False
    ), row=1, col=1)

    # Subplot 1: Sustained Speed Shaded Area
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["velocita_plot_y"],
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(56, 189, 248, 0.30)",
        line=dict(width=0),
        hoverinfo="skip",
        showlegend=False,
        connectgaps=False
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

    # Subplot 1: Sustained Speed Trace with Direction Arrow Directly in Text
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

    # Subplot 2: Direction Trace with In-Trace Vector Markers
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["direzione_deg"],
        text=df_plot_lines["dir_arrow"],
        textposition="middle center",
        mode="lines+markers+text",
        name="Direction",
        connectgaps=False,
        line=dict(color="#94a3b8", width=1.0, dash="dot"),
        marker=dict(symbol="circle", size=6.0, color="#0284c7"),
        customdata=df_plot_lines[["direzione_cardinal", "velocita_knots", "velocita_bft"]],
        hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[2]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=2, col=1)

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
            line=dict(color="#eab308", width=2.0),
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
                line=dict(color="#1e3a8a", width=2.0),
                marker=dict(size=4, color="#1e3a8a", line=dict(color="#0f172a", width=1)),
                hovertemplate="<b>Temp (Night):</b> %{y:.1f} °C<extra></extra>"
            ), row=3, col=1)

        fig.update_yaxes(title_text="°C", row=3, col=1, gridcolor="#e2e8f0", fixedrange=True)

    # Safe Vectorized Night Shading (Bounded only to visible window)
    if not daytime_only and not df_plot_lines.empty:
        days_in_slice = pd.date_range(start=t_min.floor("D"), end=t_max.ceil("D"), freq="D")
        for day in days_in_slice:
            n_start = day + pd.Timedelta(hours=19)
            n_end = day + pd.Timedelta(days=1, hours=6)
            if n_end >= t_min and n_start <= t_max:
                fig.add_vrect(
                    x0=max(n_start, t_min),
                    x1=min(n_end, t_max),
                    fillcolor="rgba(15, 23, 42, 0.04)",
                    layer="below",
                    line_width=0
                )

    # Beaufort Axis Formatting
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

    fig.update_xaxes(
        gridcolor="#e2e8f0",
        showgrid=True,
        range=[t_min, t_max]
    )

    fig.update_layout(
        height=780 if has_temp else 600,
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
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

    # 5. Render
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

    with st.expander("📋 View Data Log"):
        st.dataframe(
            df_slice.sort_values("timestamp", ascending=False),
            use_container_width=True
        )
else:
    st.warning("⚠️ No records found or waiting for CSV data connection.")
