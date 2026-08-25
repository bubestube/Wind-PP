import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Porto Pollo Weather & Wind Tracker", page_icon="🪁", layout="wide")
CSV_FILE = "porto_pollo_wind_history.csv"

st.title("🪁 Porto Pollo Kite Zone – Live Weather & Wind")
st.caption("Scraped via automated GitHub Actions | Updates automatically")

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE, on_bad_lines="skip")
    if not df.empty and "timestamp" in df.columns:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        
        latest = df.iloc[-1]
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Velocità (Speed)", f"{latest['velocita_knots']} kts")
        col2.metric("Raffica (Gusts)", f"{latest['raffica_knots']} kts")
        
        temp_val = latest.get("temperatura_c")
        col3.metric("Temperatura", f"{temp_val} °C" if pd.notnull(temp_val) else "N/A")
        col4.metric("Direzione", f"{latest['direzione_cardinal']} ({latest['direzione_deg']}°)")

        has_temp = "temperatura_c" in df.columns and df["temperatura_c"].notnull().any()

        fig = make_subplots(
            rows=3 if has_temp else 2, 
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.08,
            subplot_titles=(
                "Wind Speed & Gusts (Knots)",
                "Temperature (°C)" if has_temp else "Wind Direction (Degrees & Cardinal)",
                "Wind Direction (Degrees & Cardinal)" if has_temp else None
            ),
            row_heights=[0.45, 0.25, 0.30] if has_temp else [0.65, 0.35]
        )

        # 1. Wind Speed & Gusts
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["velocita_knots"],
            mode="lines+markers", name="Velocità",
            line=dict(color="#0284c7", width=2.5),
            hovertemplate="<b>Speed:</b> %{y:.2f} kts<extra></extra>"
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["raffica_knots"],
            mode="lines+markers", name="Raffica",
            line=dict(color="#f97316", width=2, dash="dot"),
            marker=dict(symbol="square", size=5),
            hovertemplate="<b>Gust:</b> %{y:.2f} kts<extra></extra>"
        ), row=1, col=1)

        # 2. Temperature
        dir_row = 2
        if has_temp:
            dir_row = 3
            fig.add_trace(go.Scatter(
                x=df["timestamp"], y=df["temperatura_c"],
                mode="lines+markers", name="Temperatura",
                line=dict(color="#ef4444", width=2),
                marker=dict(size=5),
                hovertemplate="<b>Temp:</b> %{y:.1f} °C<extra></extra>"
            ), row=2, col=1)
            fig.update_yaxes(title_text="°C", row=2, col=1)

        # 3. Wind Direction
        fig.add_trace(go.Scatter(
            x=df["timestamp"], y=df["direzione_deg"],
            mode="markers+lines", name="Direction",
            marker=dict(color="#10b981", size=6),
            line=dict(color="#10b981", dash="dot", width=1),
            customdata=df["direzione_cardinal"],
            hovertemplate="<b>Direction:</b> %{customdata} (%{y}°)<extra></extra>"
        ), row=dir_row, col=1)

        fig.update_yaxes(title_text="Knots", row=1, col=1)
        fig.update_yaxes(
            title_text="Degrees",
            range=[-10, 370],
            tickvals=[0, 90, 180, 270, 360],
            ticktext=["N (0°)", "E (90°)", "S (180°)", "W (270°)", "N (360°)"],
            row=dir_row, col=1
        )

        fig.update_layout(
            height=700 if has_temp else 550,
            template="plotly_white",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20)
        )

        st.plotly_chart(fig, use_container_width=True)

        with st.expander("📋 View Data Log"):
            st.dataframe(df.tail(100).sort_values("timestamp", ascending=False), use_container_width=True)
    else:
        st.info("Log file is empty. Waiting for scraper.")
else:
    st.info("No data file found yet.")
