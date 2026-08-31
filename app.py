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

# Windguru Metric Badge Helper
def get_wg_badge(val, is_speed=True):
    if pd.isna(val):
        return "#94a3b8", "#ffffff"
    if val < 11:
        return "#93c5fd", "#0f172a"  # Light blue
    elif val < 16:
        return "#38bdf8", "#0f172a"  # Cyan
    elif val < 21:
        return "#4ade80", "#0f172a"  # Green
    elif val < 26:
        return "#facc15", "#0f172a"  # Yellow
    elif val < 32:
        return "#fb923c", "#ffffff"  # Orange
    elif val < 40:
        return "#f87171", "#ffffff"  # Red
    else:
        return "#c084fc", "#ffffff"  # Purple

# Windguru Light Theme Typography
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
st.caption("Real-time weather station monitor styled after **Windguru Live Station** (*Scroll wheel to zoom, drag to pan horizontally*).")

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE, on_bad_lines="skip")
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")

        # Hard start cutoff
        df = df[df["timestamp"] >= "2026-08-27 13:41:00"]

        if df.empty:
            st.info("No data points after August 27, 2026 13:41 yet.")
            st.stop()

        latest = df.iloc[-1]

        # 1. Windguru Style Top Status Cards
        speed_bg, speed_fg = get_wg_badge(latest['velocita_knots'])
        gust_bg, gust_fg = get_wg_badge(latest['raffica_knots'])
        temp_val = latest.get("temperatura_c")

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1:
            st.markdown(f"""<div class="wg-card">
                <div class="wg-card-title">💨 Wind Speed</div>
                <div class="wg-card-val" style="color: {speed_fg}; background:{speed_bg}; border-radius:4px; padding:2px;">
                    {latest['velocita_knots']:.1f} <span style="font-size:0.9rem;">kts</span>
                </div>
            </div>""", unsafe_allow_html=True)
        with c2:
            st.markdown(f"""<div class="wg-card">
                <div class="wg-card-title">💨 Wind Gust</div>
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

        # 2. Time Window Controls
        col_filter, col_daytime = st.columns([3, 1])
        with col_filter:
            time_range = st.radio(
                "Time Window:",
                options=["Last 6 Hours", "Last 24 Hours", "Last 3 Days", "Last 7 Days", "All History"],
                index=1,
                horizontal=True
            )
        with col_daytime:
            st.write("")
            daytime_only = st.checkbox("☀️ Daytime Only (06:00 – 19:00)", value=False)

        now = df["timestamp"].max()
        if time_range == "Last 6 Hours":
            df_filtered = df[df["timestamp"] >= now - pd.Timedelta(hours=6)]
        elif time_range == "Last 24 Hours":
            df_filtered = df[df["timestamp"] >= now - pd.Timedelta(hours=24)]
        elif time_range == "Last 3 Days":
            df_filtered = df[df["timestamp"] >= now - pd.Timedelta(days=3)]
        elif time_range == "Last 7 Days":
            df_filtered = df[df["timestamp"] >= now - pd.Timedelta(days=7)]
        else:
            df_filtered = df.copy()

        if daytime_only:
            df_filtered = df_filtered[df_filtered["timestamp"].dt.hour.between(6, 18)]

        if df_filtered.empty:
            st.warning("No data points available for selected filters.")
            df_filtered = df.copy()

        has_temp = "temperatura_c" in df_filtered.columns and df_filtered["temperatura_c"].notnull().any()

        # Arrow data source
        df_for_arrows = df_filtered.copy().sort_values("timestamp").reset_index(drop=True)
        df_for_arrows["arrow_angle"] = (df_for_arrows["direzione_deg"].fillna(0) + 180) % 360

        # Gap Disconnectors for Night and >30m Outages
        df_plot = df_filtered.copy().sort_values("timestamp")
        time_diffs = df_plot["timestamp"].diff()
        gap_indices = df_plot[time_diffs > pd.Timedelta(minutes=30)].index

        if len(gap_indices) > 0:
            nan_rows = []
            for idx in gap_indices:
                prev_time = df_plot.loc[df_plot.index[df_plot.index.get_loc(idx) - 1], "timestamp"]
                nan_row = pd.DataFrame([{
                    "timestamp": prev_time + pd.Timedelta(minutes=1),
                    "velocita_knots": np.nan,
                    "raffica_knots": np.nan,
                    "temperatura_c": np.nan,
                    "direzione_deg": np.nan,
                    "direzione_cardinal": None
                }])
                nan_rows.append(nan_row)
            df_plot = pd.concat([df_plot] + nan_rows).sort_values("timestamp").reset_index(drop=True)

        # 3. Build Windguru Multi-Panel Chart
        fig = make_subplots(
            rows=3 if has_temp else 2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.035,
            subplot_titles=(
                "<b>Wind speed and gusts (knots)</b>",
                "<b>Wind direction</b>",
                "<b>Temperature (°C) – 🟡 Daytime (06-19h) | 🔵 Nighttime (19-06h)</b>" if has_temp else None
            ),
            row_heights=[0.54, 0.28, 0.18] if has_temp else [0.65, 0.35]
        )

        # --- SUBPLOT 1: WIND SPEED & GUSTS ---
        # Gusts: Red / Orange points + subtle connecting dashed line
        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"],
            y=df_plot["raffica_knots"],
            mode="lines+markers",
            name="Gust (Raffica)",
            connectgaps=False,
            line=dict(color="rgba(220, 38, 38, 0.55)", width=1.5, dash="dot"),
            marker=dict(symbol="circle", size=4.5, color="#dc2626"),
            hovertemplate="<b>Gust:</b> %{y:.1f} kts<extra></extra>"
        ), row=1, col=1)

        # Sustained Speed: Deep Windguru Blue Line + Soft Cyan Area Fill
        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"],
            y=df_plot["velocita_knots"],
            mode="lines+markers",
            name="Wind Speed (Avg)",
            fill="tozeroy",
            fillcolor="rgba(2, 132, 199, 0.12)",
            connectgaps=False,
            line=dict(color="#0284c7", width=2.2),
            marker=dict(size=4, color="#0369a1"),
            hovertemplate="<b>Speed:</b> %{y:.1f} kts<extra></extra>"
        ), row=1, col=1)

        # --- SUBPLOT 2: DIRECTION (0-360° with clean grid & arrows) ---
        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"],
            y=df_plot["direzione_deg"],
            mode="markers",
            name="Direction",
            connectgaps=False,
            marker=dict(symbol="circle", size=3.5, color="#64748b"),
            customdata=df_plot[["direzione_cardinal", "velocita_knots"]],
            hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[1]:.1f} kts<extra></extra>"
        ), row=2, col=1)

        # Adaptive Arrow Placement (>20 deg shift = instant; steady = spaced)
        steady_step = max(3, len(df_for_arrows) // 25)
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

            # Windguru color coding: Red if light (<18 kts), Green if good (>=18 kts)
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

        # --- SUBPLOT 3: TEMPERATURE STRIP (Yellow for Day, Dark Blue for Night) ---
        if has_temp:
            is_day = df_plot["timestamp"].dt.hour.between(6, 18)
            temp_day = df_plot["temperatura_c"].where(is_day, np.nan)
            temp_night = df_plot["temperatura_c"].where(~is_day, np.nan)

            # Daytime Trace (Warm Yellow / Gold)
            fig.add_trace(go.Scatter(
                x=df_plot["timestamp"],
                y=temp_day,
                mode="lines+markers",
                name="Temp (Day: 06-19h)",
                connectgaps=False,
                line=dict(color="#eab308", width=2.2),
                marker=dict(size=4, color="#eab308", line=dict(color="#ca8a04", width=1)),
                hovertemplate="<b>Temp (Day):</b> %{y:.1f} °C<extra></extra>"
            ), row=3, col=1)

            # Nighttime Trace (Dark Blue)
            if not daytime_only:
                fig.add_trace(go.Scatter(
                    x=df_plot["timestamp"],
                    y=temp_night,
                    mode="lines+markers",
                    name="Temp (Night: 19-06h)",
                    connectgaps=False,
                    line=dict(color="#1e3a8a", width=2.2),
                    marker=dict(size=4, color="#1e3a8a", line=dict(color="#0f172a", width=1)),
                    hovertemplate="<b>Temp (Night):</b> %{y:.1f} °C<extra></extra>"
                ), row=3, col=1)

            fig.update_yaxes(title_text="°C", row=3, col=1, gridcolor="#e2e8f0", fixedrange=True)

        # --- WINDGURU VERTICAL DAY/NIGHT SHADING ---
        if not daytime_only and not df_plot.empty:
            t_min = df_plot["timestamp"].min()
            t_max = df_plot["timestamp"].max()
            curr_day = t_min.floor("D")
            while curr_day <= t_max:
                night_start = curr_day + pd.Timedelta(hours=19)
                night_end = curr_day + pd.Timedelta(days=1, hours=6)
                if night_end >= t_min and night_start <= t_max:
                    fig.add_vrect(
                        x0=max(night_start, t_min),
                        x1=min(night_end, t_max),
                        fillcolor="rgba(15, 23, 42, 0.04)",
                        layer="below",
                        line_width=0
                    )
                curr_day += pd.Timedelta(days=1)

        # --- WINDGURU GRID & AXES STYLING ---
        fig.update_yaxes(
            title_text="Knots",
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
            showgrid=True
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

        # 4. Render Chart with Zoom & Pan
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

        # Numerical Log
        with st.expander(f"📋 View Numerical Data Log ({time_range})"):
            st.dataframe(
                df_filtered.sort_values("timestamp", ascending=False),
                use_container_width=True
            )
    else:
        st.info("Log file is empty. Waiting for scraper data.")
else:
    st.info("No data file found yet.")
