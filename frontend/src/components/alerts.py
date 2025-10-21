import streamlit as st
from datetime import datetime


def render_alert_item(alert, on_acknowledge=None):
    """Render a single alert item"""
    severity = alert.get('severity', 'info')
    is_critical = severity == 'critical'

    alert_class = "alert-critical" if is_critical else "alert-info"

    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown(f"""
            <div class="alert-item {alert_class}">
                <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
                    <span style="font-weight: 600; font-size: 1.1rem;">{alert.get('reason', 'Alert')}</span>
                    <span class="status-badge {'status-critical' if is_critical else 'status-warning'}" style="margin-left: 1rem;">
                        {severity.upper()}
                    </span>
                </div>
                <div style="margin-bottom: 0.5rem;">{alert.get('recommendation', '')}</div>
                <div style="font-size: 0.8rem; color: #7f8c8d;">
                    Sensor: {alert.get('sensor_type', 'Unknown')} | 
                    Value: {alert.get('value', 0)} | 
                    Time: {format_timestamp(alert.get('timestamp', ''))}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        if not alert.get('acknowledged', False):
            if st.button("Acknowledge", key=f"ack_{alert.get('id')}", use_container_width=True):
                if on_acknowledge:
                    on_acknowledge(alert.get('id'))
        else:
            st.markdown("""
                <div style="text-align: center; padding: 0.5rem; background: #e8f5e8; border-radius: 4px; color: #2e7d32;">
                    ✅ Acknowledged
                </div>
            """, unsafe_allow_html=True)


def render_alert_summary(alerts):
    """Render alert summary section"""
    critical_alerts = [a for a in alerts if a.get('severity') == 'critical' and not a.get('acknowledged')]
    warning_alerts = [a for a in alerts if a.get('severity') == 'warning' and not a.get('acknowledged')]

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Alerts", len(alerts))

    with col2:
        st.metric("Critical", len(critical_alerts), delta=None, delta_color="inverse")

    with col3:
        st.metric("Warnings", len(warning_alerts))


def format_timestamp(timestamp_str):
    """Format timestamp for display"""
    try:
        if 'T' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(timestamp_str)

        now = datetime.now()
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return timestamp_str


def create_alert_badge(count, severity="info"):
    """Create an alert badge"""
    color_map = {
        "critical": "#e74c3c",
        "warning": "#f39c12",
        "info": "#3498db"
    }

    color = color_map.get(severity, "#3498db")

    if count > 0:
        return f"""
        <span style="
            background: {color};
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            margin-left: 8px;
        ">{count}</span>
        """
    return ""