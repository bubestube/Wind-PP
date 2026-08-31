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

# --- Vectorized Helpers ---
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
st.caption("Defaulting to **Last 6 Hours** (*Scroll mouse wheel or drag horizontally to pan seamlessly through full history*).")

# 1. Cached Data Loader
@st.cache_data(ttl=60, show_spinner=False)
def load_and_prepare_data(csv_path):
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

df = load_and_prepare_data(CSV_FILE)

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

    # 3. Viewport Selection Controls
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

    # 4. Ultra-Fast In-Trace Dynamic Labels (No heavy layout annotations)
    speed_labels = [""] * len(df_plot_lines)
    gust_labels = [""] * len(df_plot_lines)

    valid_mask = df_plot_lines["velocita_knots"].notnull()
    valid_indices = df_plot_lines.index[valid_mask].tolist()

    if valid_indices:
        f_idx = valid_indices[0]
        v0 = df_plot_lines.loc[f_idx, 'velocita_knots']
        d0 = df_plot_lines.loc[f_idx, 'direzione_deg']
        a0 = deg_to_wind_arrow(d0)
        speed_labels[f_idx] = f"{v0:.1f}<br><span style='font-size:11px;'>{a0}</span>"

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
                speed_labels[idx] = f"{curr_v:.1f}<br><span style='font-size:11px;'>{arrow}</span>"
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

    # 5. Build Chart (With all points present for full timeline exploration)
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

    # Subplot 1: Gust Shaded Area
    fig.add_trace(go.Scatter(
        x=df_plot_lines["timestamp"],
        y=df_plot_lines["raffica_plot_y"],
        mode="lines",
        fill="tozeroy",
        fillcolor="rgba(239, 68, 68, 0.12)",
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
        fillcolor="rgba(56, 189, 248, 0.25)",
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

    # Subplot 1: Speed Trace with Number and Directed Arrow Below
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

    # 6. Set Initial Viewport to 6 Hours, while all previous records are ready for scrolling
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

    # 7. Render Plotly Chart
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
            df_filtered.sort_values("timestamp", ascending=False),
            use_container_width=True
        )
else:
    st.info("No data file found yet.")
