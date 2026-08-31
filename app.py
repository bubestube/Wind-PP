import datetime
import math
import os
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
        
        latest = df.iloc[-1]
        
        # 1. Top Live KPI Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Velocità (Live Speed)", f"{latest['velocita_knots']} kts")
        col2.metric("Raffica (Live Gusts)", f"{latest['raffica_knots']} kts")
        col3.metric("Direzione (Live Direction)", f"{latest['direzione_cardinal']} ({latest['direzione_deg']}°)")
        
        temp_val = latest.get("temperatura_c")
        col4.metric("Temperatura (Live Temp)", f"{temp_val} °C" if pd.notnull(temp_val) else "N/A")

        st.divider()

        # 2. Time-Range Filter Bar
        col_filter, col_spacer = st.columns([2, 3])
        with col_filter:
            time_range = st.radio(
                "Select Time Window:",
                options=["Last 6 Hours", "Last 24 Hours", "Last 3 Days", "Last 7 Days", "All History"],
                index=1,
                horizontal=True
            )

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

        if df_filtered.empty:
            df_filtered = df.copy()

        # Calculate blowing direction angle (meteorological: from + 180 = blowing to)
        df_filtered["arrow_angle"] = (df_filtered["direzione_deg"].fillna(0) + 180) % 360

        # Summary Metrics
        avg_speed = round(df_filtered["velocita_knots"].mean(), 1)
        max_gust = round(df_filtered["raffica_knots"].max(), 1)
        has_temp = "temperatura_c" in df_filtered.columns and df_filtered["temperatura_c"].notnull().any()
        temp_stats = ""
        if has_temp:
            min_temp = round(df_filtered["temperatura_c"].min(), 1)
            max_temp = round(df_filtered["temperatura_c"].max(), 1)
            temp_stats = f" | 🌡️ Temp: **{min_temp}°C - {max_temp}°C**"

        st.caption(
            f"Showing **{len(df_filtered)} datapoints** ({time_range}) | "
            f"💨 Avg Speed: **{avg_speed} kts** | 💨 Max Gust: **{max_gust} kts**"
            f"{temp_stats} | 🧭 *Arrow Color: 🟢 **≥18 kts (Go)** | 🔴 **<18 kts (Light)**.*"
        )

        # 3. Create 3 Subplots: Speed (Top), Direction (Middle), Temperature (Bottom)
        fig = make_subplots(
            rows=3 if has_temp else 2, 
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                "Wind Speed & Gusts (Knots)",
                "Wind Direction (Degrees & Vectors)",
                "Temperature (°C)" if has_temp else None
            ),
            row_heights=[0.40, 0.40, 0.20] if has_temp else [0.55, 0.45]
        )

        # Subplot 1: Wind Speed & Gusts
        fig.add_trace(go.Scatter(
            x=df_filtered["timestamp"], 
            y=df_filtered["velocita_knots"],
            mode="lines+markers", 
            name="Velocità",
            line=dict(color="#0284c7", width=2.5),
            marker=dict(size=4),
            hovertemplate="<b>Speed:</b> %{y:.2f} kts<extra></extra>"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df_filtered["timestamp"], 
            y=df_filtered["raffica_knots"],
            mode="lines+markers", 
            name="Raffica",
            line=dict(color="#f97316", width=2, dash="dot"),
            marker=dict(symbol="circle", size=4),
            hovertemplate="<b>Gust:</b> %{y:.2f} kts<extra></extra>"
        ), row=1, col=1)

        # Subplot 2: Direction Trace
        fig.add_trace(go.Scatter(
            x=df_filtered["timestamp"], 
            y=df_filtered["direzione_deg"],
            mode="markers+lines", 
            name="Direction (°)",
            marker=dict(color="#64748b", size=5),
            line=dict(color="#94a3b8", dash="dot", width=1),
            customdata=df_filtered[["direzione_cardinal", "velocita_knots"]],
            hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y}°)<br><b>Speed:</b> %{customdata[1]:.2f} kts<extra></extra>"
        ), row=2, col=1)

        # Slimmer Arrow Corpus with Preserved Stem Length in Subplot 2
        step = max(1, len(df_filtered) // 35)
        df_sub = df_filtered.iloc[::step]

        arrow_length_px = 52  # Preserved stem length

        for _, row_data in df_sub.iterrows():
            angle_deg = row_data["arrow_angle"]
            speed_val = row_data["velocita_knots"]
            
            if pd.isna(angle_deg) or pd.isna(row_data["direzione_deg"]):
                continue
            
            # Dynamic color: Green for >= 18 knots, Red for < 18 knots
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
                arrowsize=1.4,   # Slimmer arrowhead
                arrowwidth=2.0,  # Slimmer stem
                arrowcolor=arrow_color,
                opacity=0.95
            )

        # Subplot 3: Temperature (Bottom)
        if has_temp:
            fig.add_trace(go.Scatter(
                x=df_filtered["timestamp"], 
                y=df_filtered["temperatura_c"],
                mode="lines+markers", 
                name="Temperatura",
                line=dict(color="#ef4444", width=2),
                marker=dict(size=4),
                hovertemplate="<b>Temp:</b> %{y:.1f} °C<extra></extra>"
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
        with st.expander(f"📋 View Data Log ({time_range})"):
            st.dataframe(
                df_filtered.sort_values("timestamp", ascending=False),
                use_container_width=True
            )
    else:
        st.info("Log file is empty. Waiting for scraper data.")
else:
    st.info("No data file found yet.")
