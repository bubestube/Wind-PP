import datetime
import math
import os
import json
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components

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

WIND_COLORSCALE_GUST = [
    [0.00, "rgba(255, 255, 255, 0.25)"],
    [0.22, "rgba(56, 189, 248, 0.30)"],
    [0.40, "rgba(37, 99, 235, 0.35)"],
    [0.55, "rgba(34, 197, 94, 0.40)"],
    [0.70, "rgba(234, 179, 8, 0.45)"],
    [0.85, "rgba(168, 85, 247, 0.50)"],
    [1.00, "rgba(239, 68, 68, 0.55)"]
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
st.caption("Live streaming monitor with **Client-Side Progressive Infinite Pan & Zoom** (*Seamless drag without page reloads*).")

# 1. Fast Cached CSV Loader
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
        df = df[df["timestamp"] >= "2026-08-27 13:11:00"].reset_index(drop=True)
        if df.empty:
            return None

        df["velocita_bft"] = knots_to_bft(df["velocita_knots"])
        df["raffica_bft"] = knots_to_bft(df["raffica_knots"])
        df["velocita_plot_y"] = bft_to_stretched(df["velocita_bft"])
        df["raffica_plot_y"] = bft_to_stretched(df["raffica_bft"])
        df["arrow_angle"] = (df["direzione_deg"].fillna(0) + 180) % 360
        return df
    except Exception:
        return None

df_all = load_all_records(CSV_FILE)

if df_all is not None and not df_all.empty:
    latest = df_all.iloc[-1]
    latest_bft = latest['velocita_bft']
    t_global_max = df_all["timestamp"].max()
    t_global_min = df_all["timestamp"].min()

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

    has_temp = "temperatura_c" in df_all.columns and df_all["temperatura_c"].notnull().any()

    # Initial 6-Hour Time Window for the first canvas render
    v_end = t_global_max
    v_start = max(t_global_min, v_end - pd.Timedelta(hours=6))

    # Static Axis Limits & Formatting
    bft_ticks = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    bft_stretched_vals = [bft_to_stretched(b) for b in bft_ticks]
    bft_labels = [
        "0 Bft", "1 Bft", "2 Bft", "3 Bft (Gentle)", "4 Bft (Moderate)",
        "5 Bft (Fresh)", "6 Bft (Strong)", "7 Bft (Near Gale)", "8 Bft (Gale)", "9 Bft (Storm)"
    ]
    max_observed_y = df_all["raffica_plot_y"].dropna().max() if not df_all["raffica_plot_y"].dropna().empty else bft_to_stretched(7.5)
    top_y_limit = max(bft_to_stretched(7.5), max_observed_y * 1.14)

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

    # Empty Traces Initialized - JavaScript will fill data dynamically
    # Trace 0: Gust Bar Fill
    fig.add_trace(go.Bar(
        x=[], y=[],
        marker=dict(colorscale=WIND_COLORSCALE_GUST, cmin=0, cmax=8, line=dict(width=0)),
        width=2 * 60 * 1000, hoverinfo="skip", showlegend=False
    ), row=1, col=1)

    # Trace 1: Speed Bar Fill
    fig.add_trace(go.Bar(
        x=[], y=[],
        marker=dict(colorscale=WIND_COLORSCALE_SPEED, cmin=0, cmax=8, line=dict(width=0)),
        width=2 * 60 * 1000, hoverinfo="skip", showlegend=False
    ), row=1, col=1)

    # Trace 2: Gust Line
    fig.add_trace(go.Scatter(
        x=[], y=[], mode="lines+markers+text", name="Gust (Raffica)",
        textposition="top center", textfont=dict(family="Arial, sans-serif", size=10.0, color="#b91c1c"),
        connectgaps=False, line=dict(color="#0f172a", width=1.6, dash="dot"),
        marker=dict(symbol="circle", size=4.0, color="#0f172a"),
        hovertemplate="<b>Gust:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=1, col=1)

    # Trace 3: Speed Line
    fig.add_trace(go.Scatter(
        x=[], y=[], mode="lines+markers+text", name="Wind Speed (Avg)",
        textposition="bottom center", textfont=dict(family="Arial, sans-serif", size=10.0, color="#0f172a"),
        connectgaps=False, line=dict(color="#0f172a", width=2.2),
        marker=dict(size=4.0, color="#0f172a"),
        hovertemplate="<b>Speed:</b> %{customdata[0]:.1f} Bft (%{customdata[1]:.1f} kts)<br><b>Dir:</b> %{customdata[2]:.0f}°<extra></extra>"
    ), row=1, col=1)

    # Trace 4: Direction Markers
    fig.add_trace(go.Scatter(
        x=[], y=[], mode="markers", name="Direction", connectgaps=False,
        marker=dict(symbol="circle", size=3.5, color="#64748b"),
        hovertemplate="<b>Direction:</b> %{customdata[0]} (%{y:.0f}°)<br><b>Speed:</b> %{customdata[2]:.1f} Bft (%{customdata[1]:.1f} kts)<extra></extra>"
    ), row=2, col=1)

    if has_temp:
        # Trace 5: Daytime Temp
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="lines+markers", name="Temp (Day: 06-19h)",
            connectgaps=False, line=dict(color="#eab308", width=2.2),
            marker=dict(size=4, color="#eab308", line=dict(color="#ca8a04", width=1)),
            hovertemplate="<b>Temp (Day):</b> %{y:.1f} °C<extra></extra>"
        ), row=3, col=1)

        # Trace 6: Nighttime Temp
        fig.add_trace(go.Scatter(
            x=[], y=[], mode="lines+markers", name="Temp (Night: 19-06h)",
            connectgaps=False, line=dict(color="#1e3a8a", width=2.2),
            marker=dict(size=4, color="#1e3a8a", line=dict(color="#0f172a", width=1)),
            hovertemplate="<b>Temp (Night):</b> %{y:.1f} °C<extra></extra>"
        ), row=3, col=1)
        fig.update_yaxes(title_text="°C", row=3, col=1, gridcolor="#e2e8f0", fixedrange=True)

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

    fig_height = 780 if has_temp else 600
    fig.update_layout(
        height=fig_height,
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

    # Prepare Lightweight JSON Dataset for Browser-Side Slicing
    export_df = pd.DataFrame({
        "t": df_all["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
        "ts": df_all["timestamp"].astype("int64") // 10**6,
        "vk": df_all["velocita_knots"].fillna(-1).round(1),
        "vb": df_all["velocita_bft"].fillna(-1).round(2),
        "vy": df_all["velocita_plot_y"].fillna(-1).round(3),
        "rk": df_all["raffica_knots"].fillna(-1).round(1),
        "rb": df_all["raffica_bft"].fillna(-1).round(2),
        "ry": df_all["raffica_plot_y"].fillna(-1).round(3),
        "deg": df_all["direzione_deg"].fillna(-1).round(0),
        "card": df_all["direzione_cardinal"].fillna(""),
        "tc": df_all["temperatura_c"].fillna(-999).round(1) if has_temp else [None]*len(df_all),
        "hr": df_all["timestamp"].dt.hour
    })
    records_json = export_df.to_json(orient="records")
    layout_json = json.dumps(fig.to_plotly_json()["layout"])

    # 5. Client-Side Progressive Engine HTML/JS
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
        <style>
            html, body {{ margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #ffffff; }}
            #chart {{ width: 100%; height: {fig_height}px; }}
            #nav-bar {{
                display: flex; gap: 8px; align-items: center; padding: 6px 14px;
                background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-family: sans-serif; font-size: 13px;
            }}
            .btn {{
                background: #ffffff; border: 1px solid #cbd5e1; border-radius: 4px;
                padding: 4px 10px; cursor: pointer; font-weight: 500; color: #334155;
            }}
            .btn:hover {{ background: #f1f5f9; }}
            .btn-live {{ background: #ef4444; color: #ffffff; border-color: #dc2626; }}
            .btn-live:hover {{ background: #dc2626; }}
        </style>
    </head>
    <body>
        <div id="nav-bar">
            <span style="font-weight:600; color:#475569;">Quick Jump:</span>
            <button class="btn" onclick="jumpHours(6)">6h</button>
            <button class="btn" onclick="jumpHours(24)">24h</button>
            <button class="btn" onclick="jumpHours(72)">3 Days</button>
            <button class="btn" onclick="jumpHours(168)">7 Days</button>
            <button class="btn" onclick="jumpAll()">All History</button>
            <button class="btn btn-live" onclick="jumpLive()">🔴 Live View</button>
            <label style="margin-left:auto; display:flex; align-items:center; gap:4px; cursor:pointer;">
                <input type="checkbox" id="daytime-toggle" onchange="toggleDaytime()"> ☀️ Daytime Only (06-19h)
            </label>
        </div>
        <div id="chart"></div>

        <script>
            const allData = {records_json};
            const baseLayout = {layout_json};
            const hasTemp = {"true" if has_temp else "false"};
            let isDaytimeOnly = false;

            const chartDiv = document.getElementById('chart');

            const tMaxMs = allData[allData.length - 1].ts;
            const tMinMs = allData[0].ts;

            let currentStartMs = Math.max(tMinMs, tMaxMs - 6 * 3600 * 1000);
            let currentEndMs = tMaxMs;

            function sliceAndBuildTraces(startMs, endMs) {{
                const pad = 45 * 60 * 1000;
                const paddedStart = startMs - pad;
                const paddedEnd = endMs + pad;

                let visible = [];
                for (let i = 0; i < allData.length; i++) {{
                    const d = allData[i];
                    if (d.ts >= paddedStart && d.ts <= paddedEnd) {{
                        if (!isDaytimeOnly || (d.hr >= 6 && d.hr <= 18)) {{
                            visible.push(d);
                        }}
                    }}
                }}

                if (visible.length === 0) visible = [allData[allData.length - 1]];

                let xArr = [], yRaff = [], colRaff = [], yVel = [], colVel = [];
                let gustText = [], speedText = [], yDeg = [], degCustom = [];
                let customGust = [], customSpeed = [];
                let tempDay = [], tempNight = [];

                let speedArrows = [];
                let compArrows = [];

                let lastSpeedIdx = -999, lastGustIdx = -999;
                let lastDeg = -999, lastCompIdx = -999;

                const stepStride = Math.max(2, Math.floor(visible.length / 22));
                const compStride = Math.max(3, Math.floor(visible.length / 20));

                for (let i = 0; i < visible.length; i++) {{
                    const d = visible[i];
                    xArr.push(d.t);

                    const rY = d.ry >= 0 ? d.ry : null;
                    const vY = d.vy >= 0 ? d.vy : null;
                    yRaff.push(rY);
                    yVel.push(vY);
                    colRaff.push(d.rb >= 0 ? d.rb : null);
                    colVel.push(d.vb >= 0 ? d.vb : null);

                    customGust.push([d.rb, d.rk]);
                    customSpeed.push([d.vb, d.vk, d.deg]);
                    yDeg.push(d.deg >= 0 ? d.deg : null);
                    degCustom.push([d.card, d.vk, d.vb]);

                    // Dynamic Subplot 1 Labels & Decreased Stem / Increased Head Arrows
                    let sLabel = "";
                    let gLabel = "";
                    if (d.vk >= 0 && (i - lastSpeedIdx >= stepStride || i === 0 || i === visible.length - 1)) {{
                        sLabel = d.vk.toFixed(1);
                        lastSpeedIdx = i;

                        if (d.deg >= 0 && vY !== null) {{
                            const rad = ((d.deg + 180) % 360) * (Math.PI / 180.0);
                            const stemLen = 18;
                            const dx = stemLen * Math.sin(rad);
                            const dy = stemLen * Math.cos(rad);
                            speedArrows.push({{
                                x: d.t, y: vY, xref: 'x1', yref: 'y1', yshift: -24,
                                ax: -dx, ay: dy, axref: 'pixel', ayref: 'pixel',
                                showarrow: true, arrowhead: 2, arrowsize: 1.35, arrowwidth: 1.3,
                                arrowcolor: '#0f172a', opacity: 0.95
                            }});
                        }}
                    }}

                    if (d.rk >= 0 && (i - lastGustIdx >= stepStride || i === 0 || i === visible.length - 1)) {{
                        gLabel = d.rk.toFixed(1);
                        lastGustIdx = i;
                    }}
                    speedText.push(sLabel);
                    gustText.push(gLabel);

                    // Subplot 2 Direction Rotating Wind Arrows
                    if (d.deg >= 0) {{
                        const dDiff = Math.abs((d.deg - lastDeg + 180) % 360 - 180);
                        if (dDiff >= 20 || i - lastCompIdx >= compStride || i === 0) {{
                            lastDeg = d.deg;
                            lastCompIdx = i;

                            const rad = ((d.deg + 180) % 360) * (Math.PI / 180.0);
                            const arrowLen = 60;
                            const dx = arrowLen * Math.sin(rad);
                            const dy = arrowLen * Math.cos(rad);
                            const aCol = (d.vk >= 18.0) ? '#16a34a' : '#dc2626';

                            compArrows.push({{
                                x: d.t, y: d.deg, xref: 'x2', yref: 'y2',
                                ax: -dx, ay: dy, axref: 'pixel', ayref: 'pixel',
                                showarrow: true, arrowhead: 2, arrowsize: 2, arrowwidth: 1.5,
                                arrowcolor: aCol, opacity: 0.9
                            }});
                        }}
                    }}

                    if (hasTemp) {{
                        if (d.tc > -900) {{
                            if (d.hr >= 6 && d.hr <= 18) {{
                                tempDay.push(d.tc);
                                tempNight.push(null);
                            }} else {{
                                tempDay.push(null);
                                tempNight.push(d.tc);
                            }}
                        }} else {{
                            tempDay.push(null);
                            tempNight.push(null);
                        }}
                    }}
                }}

                const traces = [
                    {{ x: xArr, y: yRaff, marker: {{ color: colRaff, colorscale: WIND_COLORSCALE_GUST, cmin: 0, cmax: 8, line: {{ width: 0 }} }}, width: 2*60*1000, hoverinfo: 'skip', showlegend: false, type: 'bar' }},
                    {{ x: xArr, y: yVel, marker: {{ color: colVel, colorscale: WIND_COLORSCALE_SPEED, cmin: 0, cmax: 8, line: {{ width: 0 }} }}, width: 2*60*1000, hoverinfo: 'skip', showlegend: false, type: 'bar' }},
                    {{ x: xArr, y: yRaff, text: gustText, textposition: 'top center', textfont: {{ family: 'Arial, sans-serif', size: 10.0, color: '#b91c1c' }}, customdata: customGust, mode: 'lines+markers+text', name: 'Gust (Raffica)', connectgaps: false, line: {{ color: '#0f172a', width: 1.6, dash: 'dot' }}, marker: {{ symbol: 'circle', size: 4.0, color: '#0f172a' }}, hovertemplate: '<b>Gust:</b> %{{customdata[0]:.1f}} Bft (%{{customdata[1]:.1f}} kts)<extra></extra>', type: 'scatter' }},
                    {{ x: xArr, y: yVel, text: speedText, textposition: 'bottom center', textfont: {{ family: 'Arial, sans-serif', size: 10.0, color: '#0f172a' }}, customdata: customSpeed, mode: 'lines+markers+text', name: 'Wind Speed (Avg)', connectgaps: false, line: {{ color: '#0f172a', width: 2.2 }}, marker: {{ size: 4.0, color: '#0f172a' }}, hovertemplate: '<b>Speed:</b> %{{customdata[0]:.1f}} Bft (%{{customdata[1]:.1f}} kts)<br><b>Dir:</b> %{{customdata[2]:.0f}}°<extra></extra>', type: 'scatter' }},
                    {{ x: xArr, y: yDeg, mode: 'markers', name: 'Direction', connectgaps: false, marker: {{ symbol: 'circle', size: 3.5, color: '#64748b' }}, customdata: degCustom, hovertemplate: '<b>Direction:</b> %{{customdata[0]}} (%{{y:.0f}}°)<br><b>Speed:</b> %{{customdata[2]:.1f}} Bft (%{{customdata[1]:.1f}} kts)<extra></extra>', type: 'scatter', xaxis: 'x', yaxis: 'y2' }}
                ];

                if (hasTemp) {{
                    traces.push({{ x: xArr, y: tempDay, mode: 'lines+markers', name: 'Temp (Day: 06-19h)', connectgaps: false, line: {{ color: '#eab308', width: 2.2 }}, marker: {{ size: 4, color: '#eab308', line: {{ color: '#ca8a04', width: 1 }} }}, hovertemplate: '<b>Temp (Day):</b> %{{y:.1f}} °C<extra></extra>', type: 'scatter', xaxis: 'x', yaxis: 'y3' }});
                    if (!isDaytimeOnly) {{
                        traces.push({{ x: xArr, y: tempNight, mode: 'lines+markers', name: 'Temp (Night: 19-06h)', connectgaps: false, line: {{ color: '#1e3a8a', width: 2.2 }}, marker: {{ size: 4, color: '#1e3a8a', line: {{ color: '#0f172a', width: 1 }} }}, hovertemplate: '<b>Temp (Night):</b> %{{y:.1f}} °C<extra></extra>', type: 'scatter', xaxis: 'x', yaxis: 'y3' }});
                    }}
                }}

                return {{ traces, annotations: speedArrows.concat(compArrows) }};
            }}

            const initialRender = sliceAndBuildTraces(currentStartMs, currentEndMs);
            baseLayout.annotations = initialRender.annotations;
            baseLayout.xaxis.range = [
                new Date(currentStartMs).toISOString().replace('T', ' ').substring(0, 19),
                new Date(currentEndMs).toISOString().replace('T', ' ').substring(0, 19)
            ];

            Plotly.newPlot(chartDiv, initialRender.traces, baseLayout, {{
                scrollZoom: true,
                displayModeBar: true,
                displaylogo: false,
                modeBarButtonsToRemove: ['lasso2d', 'select2d']
            }});

            // Seamless Client-Side Infinite Pan / Scroll Listener
            let debounceTimer = null;
            chartDiv.on('plotly_relayout', function(eventdata) {{
                const x0 = eventdata['xaxis.range[0]'] || (eventdata['xaxis.range'] && eventdata['xaxis.range'][0]);
                const x1 = eventdata['xaxis.range[1]'] || (eventdata['xaxis.range'] && eventdata['xaxis.range'][1]);

                if (x0 && x1) {{
                    const sMs = new Date(x0).getTime();
                    const eMs = new Date(x1).getTime();

                    if (!isNaN(sMs) && !isNaN(eMs)) {{
                        currentStartMs = sMs;
                        currentEndMs = eMs;

                        clearTimeout(debounceTimer);
                        debounceTimer = setTimeout(function() {{
                            const updated = sliceAndBuildTraces(currentStartMs, currentEndMs);
                            baseLayout.annotations = updated.annotations;
                            baseLayout.xaxis.range = [x0, x1];
                            // Instant in-place Plotly React (Zero page reload)
                            Plotly.react(chartDiv, updated.traces, baseLayout);
                        }}, 120);
                    }}
                }}
            }});

            window.jumpHours = function(hrs) {{
                currentEndMs = tMaxMs;
                currentStartMs = Math.max(tMinMs, tMaxMs - hrs * 3600 * 1000);
                updateChartWindow();
            }};

            window.jumpAll = function() {{
                currentStartMs = tMinMs;
                currentEndMs = tMaxMs;
                updateChartWindow();
            }};

            window.jumpLive = function() {{
                jumpHours(6);
            }};

            window.toggleDaytime = function() {{
                isDaytimeOnly = document.getElementById('daytime-toggle').checked;
                updateChartWindow();
            }};

            function updateChartWindow() {{
                const updated = sliceAndBuildTraces(currentStartMs, currentEndMs);
                baseLayout.annotations = updated.annotations;
                baseLayout.xaxis.range = [
                    new Date(currentStartMs).toISOString().replace('T', ' ').substring(0, 19),
                    new Date(currentEndMs).toISOString().replace('T', ' ').substring(0, 19)
                ];
                Plotly.react(chartDiv, updated.traces, baseLayout);
            }}
        </script>
    </body>
    </html>
    """

    components.html(html_code, height=fig_height + 50)

    with st.expander("📋 View Full Data Log"):
        st.dataframe(
            df_all.sort_values("timestamp", ascending=False),
            use_container_width=True
        )
else:
    st.info("No data file found yet.")
