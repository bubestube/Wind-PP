import datetime
import math
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="Porto Pollo – Windguru Station View",
    page_icon="🪁",
    layout="wide"
)

CSV_FILE = "porto_pollo_wind_history.csv"

# Custom Windguru Palette Mapping (Knots)
def get_windguru_color(knots):
    if pd.isna(knots):
        return "#94a3b8"
    if knots < 7:
        return "#e2e8f0"  # Very light / white-blue
    elif knots < 11:
        return "#93c5fd"  # Soft blue
    elif knots < 15:
        return "#3b82f6"  # Blue
    elif knots < 19:
        return "#10b981"  # Emerald green (kiting entry)
    elif knots < 23:
        return "#84cc16"  # Lime / yellow-green
    elif knots < 27:
        return "#eab308"  # Yellow-orange
    elif knots < 33:
        return "#f97316"  # Vivid orange
    elif knots < 40:
        return "#ef4444"  # Red
    else:
        return "#a855f7"  # Purple / Storm

st.markdown("""
    <style>
    .main { background-color: #0f172a; }
    h1, h2, h3, p, span, label { color: #f8fafc !important; }
    </style>
""", unsafe_allow_html=True)

st.title("🪁 Porto Pollo Kite Zone – Windguru Station View")
st.caption("Live wind station history styled after Windguru. *Use your mouse wheel on the graph to zoom in/out in time.*")

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

        # 1. Top Windguru Style Live Header
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        
        kpi1.metric("Current Speed", f"{latest['velocita_knots']} kts")
        kpi2.metric("Current Gust", f"{latest['raffica_knots']} kts")
        kpi3.metric("Direction", f"{latest['direzione_cardinal']} ({latest['direzione_deg']}°)")
        
        temp_val = latest.get("temperatura_c")
        kpi4.metric("Temperature", f"{temp_val} °C" if pd.notnull(temp_val) else "N/A")
        kpi5.metric("Last Reading", latest["timestamp"].strftime("%H:%M (%d %b)"))

        st.divider()

        # 2. Time-Range & Daytime Filter Bar
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

        # Filter dataset
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
            st.warning("No data points available for the selected filters.")
            df_filtered = df.copy()

        # Summary Stats
        avg_speed = round(df_filtered["velocita_knots"].mean(), 1)
        max_gust = round(df_filtered["raffica_knots"].max(), 1)
        has_temp = "temperatura_c" in df_filtered.columns and df_filtered["temperatura_c"].notnull().any()

        # Base angles & data copy
        df_for_arrows = df_filtered.copy().sort_values("timestamp").reset_index(drop=True)
        df_for_arrows["arrow_angle"] = (df_for_arrows["direzione_deg"].fillna(0) + 180) % 360

        # Create Gap Breakers for Nights / >30m outages
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

        # 3. Windguru Tri-Panel Subplot Layout
        fig = make_subplots(
            rows=3 if has_temp else 2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            subplot_titles=(
                "💨 Wind Speed & Gusts (kts)",
                "🧭 Wind Direction (° & Vectors)",
                "🌡️ Temperature (°C)" if has_temp else None
            ),
            row_heights=[0.55, 0.28, 0.17] if has_temp else [0.68, 0.32]
        )

        # --- SUBPLOT 1: WIND SPEED & GUSTS ---
        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"],
            y=df_plot["raffica_knots"],
            mode="lines+markers",
            name="Gust (Raffica)",
            connectgaps=False,
            line=dict(color="#f97316", width=1.5, dash="dot"),
            marker=dict(symbol="circle", size=4, color="#ea580c"),
            hovertemplate="<b>Gust:</b> %{y:.1f} kts<extra></extra>"
        ), row=1, col=1)

        point_colors = [get_windguru_color(k) for k in df_plot["velocita_knots"]]

        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"],
            y=df_plot["velocita_knots"],
            mode="lines+markers",
            name="Speed (Velocità)",
            fill="tozeroy",
            fillcolor="rgba(14, 165, 233, 0.18)",
            connectgaps=False,
            line=dict(color="#38bdf8", width=2.5),
            marker=dict(
                size=6,
                color=point_colors,
                line=dict(color="#0f172a", width=1)
            ),
            hovertemplate="<b>Speed:</b> %{y:.1f} kts<extra></extra>"
        ), row=1, col=1)

        # --- SUBPLOT 2: DIRECTION DEGREES & ARROW BAND ---
        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"],
            y=df_plot["direzione_deg"],
            mode="lines+markers",
            name="Direction",
            connectgaps=False,
            line=dict(color="#64748b", width=1, dash="dot"),
            marker=dict(symbol="circle", size=3, color="#94a3b8"),
            customdata=df_plot[["direzione_cardinal", "velocita_knots"]],
            hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y}°)<br><b>Speed:</b> %{customdata[1]:.1f} kts<extra></extra>"
        ), row=2, col=1)

        # Adaptive Arrow Placement
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
        arrow_length_px = 46

        for _, row_data in df_sub.iterrows():
            angle_deg = row_data["arrow_angle"]
            speed_val = row_data["velocita_knots"]

            if pd.isna(angle_deg) or pd.isna(row_data["direzione_deg"]):
                continue

            arrow_color = get_windguru_color(speed_val)

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
                arrowsize=1.1,
                arrowwidth=2.2,
                arrowcolor=arrow_color,
                opacity=0.95
            )

        # --- SUBPLOT 3: TEMPERATURE STRIP ---
        if has_temp:
            fig.add_trace(go.Scatter(
                x=df_plot["timestamp"],
                y=df_plot["temperatura_c"],
                mode="lines+markers",
                name="Temperature",
                connectgaps=False,
                line=dict(color="#f43f5e", width=2.0),
                marker=dict(size=4, color="#fb7185"),
                hovertemplate="<b>Temp:</b> %{y:.1f} °C<extra></extra>"
            ), row=3, col=1)
            fig.update_yaxes(title_text="°C", row=3, col=1, gridcolor="#334155", fixedrange=True)

        # --- AXES & WINDGURU THEME FORMATTING ---
        # fixedrange=True locks Y-axes so wheel scrolling only zooms horizontally (time)
        fig.update_yaxes(
            title_text="Knots",
            row=1, col=1,
            gridcolor="#334155",
            zerolinecolor="#475569",
            fixedrange=True
        )
        fig.update_yaxes(
            title_text="Direction",
            range=[-40, 400],
            tickvals=[0, 90, 180, 270, 360],
            ticktext=["N", "E", "S", "W", "N"],
            row=2, col=1,
            gridcolor="#334155",
            fixedrange=True
        )
        fig.update_xaxes(
            gridcolor="#334155",
            showgrid=True
        )

        fig.update_layout(
            height=820 if has_temp else 640,
            paper_bgcolor="#0f172a",
            plot_bgcolor="#1e293b",
            font=dict(color="#e2e8f0"),
            hovermode="x unified",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(15, 23, 42, 0.7)"
            ),
            margin=dict(l=30, r=20, t=50, b=30)
        )

        # 4. Render with Scroll-Wheel Zooming enabled
        st.plotly_chart(
            fig,
            use_container_width=True,
            config={
                "scrollZoom": True,            # ⬅️ Enables scroll wheel zooming
                "displayModeBar": True,
                "displaylogo": False,
                "modeBarButtonsToRemove": ["lasso2d", "select2d"]
            }
        )

        # Data Table
        with st.expander(f"📋 View Numerical Log ({time_range})"):
            st.dataframe(
                df_filtered.sort_values("timestamp", ascending=False),
                use_container_width=True
            )
    else:
        st.info("Log file is empty. Waiting for scraper data.")
else:
    st.info("No data file found yet.")
