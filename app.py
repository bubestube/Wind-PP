import datetime
import math
import os
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="Porto Pollo Weather & Wind Tracker", 
    page_icon="🪁", 
    layout="wide"
)

CSV_FILE = "porto_pollo_wind_history.csv"

st.title("🪁 Porto Pollo Kite Zone – Live Weather & Wind")
st.caption("Automated scraper via GitHub Actions | Real-time weather dashboard")

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
        
        # 1. Top Live KPI Cards (Always current latest reading)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Velocità (Live Speed)", f"{latest['velocita_knots']} kts")
        col2.metric("Raffica (Live Gusts)", f"{latest['raffica_knots']} kts")
        col3.metric("Direzione (Live Direction)", f"{latest['direzione_cardinal']} ({latest['direzione_deg']}°)")
        
        temp_val = latest.get("temperatura_c")
        col4.metric("Temperatura (Live Temp)", f"{temp_val} °C" if pd.notnull(temp_val) else "N/A")

        st.divider()

        # 2. Time-Range & Daytime Filter Bar
        col_filter, col_daytime = st.columns([3, 1])
        with col_filter:
            time_range = st.radio(
                "Select Time Window:",
                options=["Last 6 Hours", "Last 24 Hours", "Last 3 Days", "Last 7 Days", "All History"],
                index=1,
                horizontal=True
            )
        with col_daytime:
            st.write("")  # Alignment spacer
            daytime_only = st.checkbox("☀️ Daytime Only (06:00 – 19:00)", value=False)

        # Apply Time-Range Filtering
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

        # Apply Daytime (06:00 to 19:00) Filter
        if daytime_only:
            df_filtered = df_filtered[df_filtered["timestamp"].dt.hour.between(6, 18)]

        if df_filtered.empty:
            st.warning("No data points available for the selected filters. Showing all recent records.")
            df_filtered = df.copy()

        # Summary Metrics
        avg_speed = round(df_filtered["velocita_knots"].mean(), 1)
        max_gust = round(df_filtered["raffica_knots"].max(), 1)
        has_temp = "temperatura_c" in df_filtered.columns and df_filtered["temperatura_c"].notnull().any()
        temp_stats = ""
        if has_temp:
            min_temp = round(df_filtered["temperatura_c"].min(), 1)
            max_temp = round(df_filtered["temperatura_c"].max(), 1)
            temp_stats = f" | 🌡️ Temp: **{min_temp}°C - {max_temp}°C** (🟡 Day / 🔵 Night)"

        daytime_label = " (06:00–19:00)" if daytime_only else ""
        st.caption(
            f"Showing **{len(df_filtered)} datapoints** ({time_range}{daytime_label}) | "
            f"💨 Avg Speed: **{avg_speed} kts** | 💨 Max Gust: **{max_gust} kts**"
            f"{temp_stats} | 🧭 *Arrow Color: 🟢 **≥18 kts (Go)** | 🔴 **<18 kts (Light)**.*"
        )

        # Vector Arrow Data Source
        df_for_arrows = df_filtered.copy().sort_values("timestamp").reset_index(drop=True)
        df_for_arrows["arrow_angle"] = (df_for_arrows["direzione_deg"].fillna(0) + 180) % 360

        # Insert NaN rows for line breaks across >30min gaps
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

        # 3. Subplots
        fig = make_subplots(
            rows=3 if has_temp else 2, 
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                "Wind Speed & Gusts (Knots)",
                "Wind Direction (Degrees & Vectors)",
                "Temperature (°C) – 🟡 Daytime (06-19h) | 🔵 Nighttime (19-06h)" if has_temp else None
            ),
            row_heights=[0.40, 0.40, 0.20] if has_temp else [0.55, 0.45]
        )

        # Subplot 1: Wind Speed & Gusts
        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"], 
            y=df_plot["velocita_knots"],
            mode="lines+markers", 
            name="Velocità",
            connectgaps=False,
            line=dict(color="#0284c7", width=2.5),
            marker=dict(size=4),
            hovertemplate="<b>Speed:</b> %{y:.2f} kts<extra></extra>"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"], 
            y=df_plot["raffica_knots"],
            mode="lines+markers", 
            name="Raffica",
            connectgaps=False,
            line=dict(color="#f97316", width=2, dash="dot"),
            marker=dict(symbol="circle", size=4),
            hovertemplate="<b>Gust:</b> %{y:.2f} kts<extra></extra>"
        ), row=1, col=1)

        # Subplot 2: Direction Trace
        fig.add_trace(go.Scatter(
            x=df_plot["timestamp"], 
            y=df_plot["direzione_deg"],
            mode="markers+lines", 
            name="Direction (°)",
            connectgaps=False,
            marker=dict(color="#64748b", size=5),
            line=dict(color="#94a3b8", dash="dot", width=1),
            customdata=df_plot[["direzione_cardinal", "velocita_knots"]],
            hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y}°)<br><b>Speed:</b> %{customdata[1]:.2f} kts<extra></extra>"
        ), row=2, col=1)

        # --- Adaptive Arrow Selection: Direct Angular Delta ---
        # Base fallback distance for steady wind (e.g. at most 1 arrow every 5-8 points)
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
                
                # Compute absolute angular shift (shortest path on 360 circle)
                delta_deg = abs((curr_deg - last_deg + 180) % 360 - 180)
                points_since_last = i - last_idx

                # Condition 1: Wind shifted significantly (>= 15 degrees) -> Show arrow
                # Condition 2: Wind is steady, but reached the fallback interval -> Show arrow
                if delta_deg >= 15.0 or points_since_last >= steady_step:
                    selected_indices.append(i)
                    last_idx = i
                    last_deg = curr_deg

        df_sub = df_for_arrows.iloc[selected_indices]
        arrow_length_px = 52

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
                arrowsize=1.1,
                arrowwidth=2.0,
                arrowcolor=arrow_color,
                opacity=0.95
            )

        # Subplot 3: Temperature
        if has_temp:
            is_day = df_plot["timestamp"].dt.hour.between(6, 18)
            temp_day = df_plot["temperatura_c"].where(is_day, np.nan)
            temp_night = df_plot["temperatura_c"].where(~is_day, np.nan)

            fig.add_trace(go.Scatter(
                x=df_plot["timestamp"], 
                y=temp_day,
                mode="lines+markers", 
                name="Temp (Day: 06-19h)",
                connectgaps=False,
                line=dict(color="#eab308", width=2.5),
                marker=dict(size=4.5, color="#eab308", line=dict(color="#ca8a04", width=1)),
                hovertemplate="<b>Temp (Day):</b> %{y:.1f} °C<extra></extra>"
            ), row=3, col=1)

            if not daytime_only:
                fig.add_trace(go.Scatter(
                    x=df_plot["timestamp"], 
                    y=temp_night,
                    mode="lines+markers", 
                    name="Temp (Night: 19-06h)",
                    connectgaps=False,
                    line=dict(color="#1e3a8a", width=2.5),
                    marker=dict(size=4.5, color="#1e3a8a", line=dict(color="#0f172a", width=1)),
                    hovertemplate="<b>Temp (Night):</b> %{y:.1f} °C<extra></extra>"
                ), row=3, col=1)

            fig.update_yaxes(title_text="°C", row=3, col=1)

        # Axis Formatting
        fig.update_yaxes(title_text="Knots", row=1, col=1)
        fig.update_yaxes(
            title_text="Degrees",
            range=[-40, 400],
            tickvals=[0, 90, 180, 270, 360],
            ticktext=["N (0°)", "E (90°)", "S (180°)", "W (270°)", "N (360°)"],
            row=2, col=1
        )

        fig.update_layout(
            height=780 if has_temp else 600,
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Filtered Log Table
        with st.expander(f"📋 View Data Log ({time_range}{daytime_label})"):
            st.dataframe(
                df_filtered.sort_values("timestamp", ascending=False),
                use_container_width=True
            )
    else:
        st.info("Log file is empty. Waiting for scraper data.")
else:
    st.info("No data file found yet.")
