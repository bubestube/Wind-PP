import os
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(page_title="Porto Pollo Wind Tracker", page_icon="🪁", layout="wide")
CSV_FILE = "porto_pollo_wind_history.csv"

st.title("🪁 Porto Pollo Kite Zone – Wind Monitor")

if os.path.exists(CSV_FILE):
    df = pd.read_csv(CSV_FILE, on_bad_lines="skip")
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
    
    latest = df.iloc[-1]
    col1, col2, col3 = st.columns(3)
    col1.metric("Velocità", f"{latest['velocita_knots']} kts")
    col2.metric("Raffica", f"{latest['raffica_knots']} kts")
    col3.metric("Direzione", f"{latest['direzione_cardinal']} ({latest['direzione_deg']}°)")

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=("Speed & Gusts", "Direction"))
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["velocita_knots"], mode="lines+markers", name="Speed", line=dict(color="#0284c7")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["raffica_knots"], mode="lines+markers", name="Gust", line=dict(color="#f97316", dash="dot")), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["timestamp"], y=df["direzione_deg"], mode="markers", name="Direction", marker=dict(color="#10b981", size=7)), row=2, col=1)
    
    fig.update_layout(height=550, template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No data yet. Waiting for scraper.")