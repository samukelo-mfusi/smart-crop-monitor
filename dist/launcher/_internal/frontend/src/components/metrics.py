import streamlit as st


def render_metric_card(value, label, unit="", trend=None, card_class=""):
    """Render a metric card with optional trend indicator"""
    trend_icon = ""
    trend_color = ""

    if trend == "up":
        trend_icon = "↗"
        trend_color = "#27ae60"
    elif trend == "down":
        trend_icon = "↘"
        trend_color = "#e74c3c"
    elif trend == "stable":
        trend_icon = "→"
        trend_color = "#f39c12"

    st.markdown(f"""
        <div class="metric-card {card_class}">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}{unit}</div>
            <div class="metric-unit">
                {f'<span style="color: {trend_color};">{trend_icon}</span>' if trend_icon else ''}
            </div>
        </div>
    """, unsafe_allow_html=True)


def render_moisture_progress(value, zone_name):
    """Render moisture level with progress bar"""
    status_text, status_class, status_color = get_moisture_status(value)

    st.markdown(f"""
        <div style="margin-bottom: 1rem;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                <span style="font-weight: 600;">{zone_name}</span>
                <span style="font-weight: 700; color: {status_color};">{value:.1f}%</span>
            </div>
            <div class="progress-container">
                <div class="progress-bar progress-moisture" style="width: {min(value, 100)}%;"></div>
            </div>
            <div style="display: flex; justify-content: space-between; margin-top: 0.25rem;">
                <span style="font-size: 0.7rem; color: #7f8c8d;">Dry</span>
                <span style="font-size: 0.7rem; color: #7f8c8d;">Optimal</span>
            </div>
            <div style="text-align: center; margin-top: 0.5rem;">
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)


def get_moisture_status(moisture_level):
    """Get moisture status and styling"""
    if moisture_level >= 60:
        return "Optimal", "status-wet", "#27ae60"
    elif moisture_level >= 40:
        return "Moderate", "status-active", "#f39c12"
    else:
        return "Dry", "status-critical", "#e74c3c"


def render_system_health_indicators(metrics):
    """Render system health indicators"""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        uptime = metrics.get('uptime', 0)
        status = "Excellent" if uptime > 95 else "Good" if uptime > 85 else "Needs Attention"
        color = "#27ae60" if uptime > 95 else "#f39c12" if uptime > 85 else "#e74c3c"
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 2rem; color: {color}; margin-bottom: 0.5rem;">●</div>
                <div style="font-weight: 600;">Uptime</div>
                <div style="font-size: 0.8rem; color: #7f8c8d;">{status}</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        data_points = metrics.get('data_points_today', 0)
        status = "Excellent" if data_points > 40 else "Good" if data_points > 20 else "Low"
        color = "#27ae60" if data_points > 40 else "#f39c12" if data_points > 20 else "#e74c3c"
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 2rem; color: {color}; margin-bottom: 0.5rem;">●</div>
                <div style="font-weight: 600;">Data Quality</div>
                <div style="font-size: 0.8rem; color: #7f8c8d;">{status}</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        zones_active = metrics.get('zones_active', 0)
        status = "Optimal" if zones_active >= 2 else "Partial"
        color = "#27ae60" if zones_active >= 2 else "#f39c12"
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 2rem; color: {color}; margin-bottom: 0.5rem;">●</div>
                <div style="font-weight: 600;">Coverage</div>
                <div style="font-size: 0.8rem; color: #7f8c8d;">{status}</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        energy_saved = metrics.get('energy_saved', 0)
        status = "Excellent" if energy_saved > 80 else "Good" if energy_saved > 60 else "Moderate"
        color = "#27ae60" if energy_saved > 80 else "#f39c12" if energy_saved > 60 else "#e74c3c"
        st.markdown(f"""
            <div style="text-align: center;">
                <div style="font-size: 2rem; color: {color}; margin-bottom: 0.5rem;">●</div>
                <div style="font-weight: 600;">Efficiency</div>
                <div style="font-size: 0.8rem; color: #7f8c8d;">{status}</div>
            </div>
        """, unsafe_allow_html=True)