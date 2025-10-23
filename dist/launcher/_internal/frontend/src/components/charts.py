import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta


def create_moisture_trend_chart(historical_data):
    """Soil moisture trend chart"""
    if not historical_data:
        return create_empty_chart("No historical data available")

    df = pd.DataFrame(historical_data)

    fig = go.Figure()

    # Moisture trend line
    fig.add_trace(go.Scatter(
        x=df['date'],
        y=df['avg_moisture'],
        mode='lines+markers',
        name='Soil Moisture',
        line=dict(color='#3498db', width=3),
        marker=dict(size=6, color='#2980b9')
    ))

    # Optimal range
    fig.add_hrect(
        y0=60, y1=100,
        fillcolor="green", opacity=0.1,
        layer="below", line_width=0,
        annotation_text="Optimal Range",
        annotation_position="top left"
    )

    # Moderate range
    fig.add_hrect(
        y0=40, y1=60,
        fillcolor="yellow", opacity=0.1,
        layer="below", line_width=0,
        annotation_text="Moderate Range",
        annotation_position="top left"
    )

    # Critical range
    fig.add_hrect(
        y0=0, y1=40,
        fillcolor="red", opacity=0.1,
        layer="below", line_width=0,
        annotation_text="Critical Range",
        annotation_position="top left"
    )

    fig.update_layout(
        title="Soil Moisture Trends (Last 7 Days)",
        xaxis_title="Date",
        yaxis_title="Moisture Level (%)",
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=True
    )

    return fig


def create_environmental_chart(sensor_data):
    """Environmental conditions chart"""
    if not sensor_data:
        return create_empty_chart("No sensor data available")

    # Group data by timestamp and sensor type
    df = pd.DataFrame(sensor_data)
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Get last 24 hours of data
    cutoff = datetime.now() - timedelta(hours=24)
    recent_data = df[df['timestamp'] >= cutoff]

    if recent_data.empty:
        return create_empty_chart("No recent sensor data")

    # Subplots
    fig = go.Figure()

    # Temperature
    temp_data = recent_data[recent_data['sensor_type'] == 'temperature']
    if not temp_data.empty:
        fig.add_trace(go.Scatter(
            x=temp_data['timestamp'],
            y=temp_data['value'],
            mode='lines',
            name='Temperature (°C)',
            line=dict(color='#e74c3c', width=2)
        ))

    # Humidity
    humidity_data = recent_data[recent_data['sensor_type'] == 'humidity']
    if not humidity_data.empty:
        fig.add_trace(go.Scatter(
            x=humidity_data['timestamp'],
            y=humidity_data['value'],
            mode='lines',
            name='Humidity (%)',
            line=dict(color='#3498db', width=2),
            yaxis='y2'
        ))

    fig.update_layout(
        title="Environmental Conditions (Last 24 Hours)",
        xaxis_title="Time",
        yaxis=dict(
            title="Temperature (°C)",
            titlefont=dict(color='#e74c3c'),
            tickfont=dict(color='#e74c3c')
        ),
        yaxis2=dict(
            title="Humidity (%)",
            titlefont=dict(color='#3498db'),
            tickfont=dict(color='#3498db'),
            anchor="x",
            overlaying="y",
            side="right"
        ),
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def create_water_usage_chart(historical_data):
    """Water usage analysis chart"""
    if not historical_data:
        return create_empty_chart("No water usage data available")

    df = pd.DataFrame(historical_data)

    fig = go.Figure()

    # Water need estimation
    if 'water_need' in df.columns:
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['water_need'],
            name='Estimated Water Need',
            marker_color='#3498db',
            opacity=0.8
        ))

    # Moisture levels
    if 'avg_moisture' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['avg_moisture'],
            mode='lines+markers',
            name='Soil Moisture',
            line=dict(color='#27ae60', width=3),
            yaxis='y2'
        ))

    fig.update_layout(
        title="Water Usage Analysis",
        xaxis_title="Date",
        yaxis=dict(
            title="Water Need (L)",
            titlefont=dict(color='#3498db'),
            tickfont=dict(color='#3498db')
        ),
        yaxis2=dict(
            title="Moisture (%)",
            titlefont=dict(color='#27ae60'),
            tickfont=dict(color='#27ae60'),
            anchor="x",
            overlaying="y",
            side="right"
        ),
        height=350,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def create_system_metrics_gauge(value, title, min_val=0, max_val=100):
    """Gauge chart for system metrics"""
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        title={'text': title},
        number={'suffix': "%", 'font': {'size': 20}},
        gauge={
            'axis': {'range': [min_val, max_val]},
            'bar': {'color': "#3498db"},
            'steps': [
                {'range': [0, 50], 'color': "lightgray"},
                {'range': [50, 80], 'color': "yellow"},
                {'range': [80, 100], 'color': "lightgreen"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig


def create_empty_chart(message):
    """Empty chart with a message"""
    fig = go.Figure()
    fig.update_layout(
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[{
            "text": message,
            "xref": "paper",
            "yref": "paper",
            "showarrow": False,
            "font": {"size": 16}
        }],
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig