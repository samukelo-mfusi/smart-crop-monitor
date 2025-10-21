import streamlit as st
import re


def render_login_form(on_login, on_switch_to_register):
    """Render login form"""
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        submitted = st.form_submit_button("Sign In", use_container_width=True)

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                on_login(username, password)

    st.markdown('<div style="text-align: center; margin-top: 1.5rem;">', unsafe_allow_html=True)
    st.markdown('<p style="color: #7f8c8d;">Don\'t have an account?</p>', unsafe_allow_html=True)
    if st.button("Create Account", key="switch_to_register"):
        on_switch_to_register()
    st.markdown('</div>', unsafe_allow_html=True)


def render_register_form(on_register, on_switch_to_login):
    """Render registration form"""
    with st.form("register_form"):
        full_name = st.text_input("Full Name", placeholder="Enter your full name")
        username = st.text_input("Username", placeholder="Choose a username")
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Create a strong password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")

        submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            errors = validate_registration_form(full_name, username, email, password, confirm_password)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                on_register({
                    "full_name": full_name,
                    "username": username,
                    "email": email,
                    "password": password
                })

    st.markdown('<div style="text-align: center; margin-top: 1.5rem;">', unsafe_allow_html=True)
    st.markdown('<p style="color: #7f8c8d;">Already have an account?</p>', unsafe_allow_html=True)
    if st.button("Sign In", key="switch_to_login"):
        on_switch_to_login()
    st.markdown('</div>', unsafe_allow_html=True)


def validate_registration_form(full_name, username, email, password, confirm_password):
    """Validate registration form data"""
    errors = []

    if not all([username, email, full_name, password, confirm_password]):
        errors.append("Please fill in all fields")

    if not is_valid_email(email):
        errors.append("Please enter a valid email address")

    if password != confirm_password:
        errors.append("Passwords do not match")

    if not is_strong_password(password):
        errors.append("Password must be at least 8 characters with uppercase, lowercase, and numbers")

    if len(username) < 3:
        errors.append("Username must be at least 3 characters long")

    return errors


def is_valid_email(email):
    """Check if email has valid format"""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def is_strong_password(password):
    """Check if password meets strength requirements"""
    return (len(password) >= 8 and
            any(char.isdigit() for char in password) and
            any(char.isupper() for char in password) and
            any(char.islower() for char in password))


def render_irrigation_form(zone, current_moisture, on_irrigate):
    """Render irrigation control form"""
    status_text, status_class, _ = get_moisture_status(current_moisture)

    st.markdown(f"""
        <div style="text-align: center; margin: 1rem 0;">
            <div style="font-size: 2rem; color: #2c3e50; margin-bottom: 0.5rem;">{current_moisture:.1f}%</div>
            <span class="status-badge {status_class}">{status_text}</span>
        </div>
    """, unsafe_allow_html=True)

    with st.form(f"{zone}_irrigation"):
        duration = st.slider("Irrigation Duration (minutes)", 1, 30, 5, key=f"{zone}_duration")

        if st.form_submit_button("💧 Start Irrigation", use_container_width=True):
            on_irrigate(zone, duration)


def render_settings_form(current_settings, on_save):
    """Render system settings form"""
    with st.form("settings_form"):
        col1, col2 = st.columns(2)

        with col1:
            soil_threshold = st.slider(
                "Soil Moisture Alert Threshold (%)",
                min_value=20,
                max_value=80,
                value=int(current_settings.get('soil_moisture_threshold', 40)),
                help="Alert when soil moisture drops below this level"
            )

        with col2:
            temp_threshold = st.slider(
                "Temperature Alert Threshold (°C)",
                min_value=25,
                max_value=45,
                value=int(current_settings.get('temperature_threshold', 35)),
                help="Alert when temperature exceeds this level"
            )

        if st.form_submit_button("Save Settings", use_container_width=True):
            updates = {
                'soil_moisture_threshold': str(soil_threshold),
                'temperature_threshold': str(temp_threshold)
            }
            on_save(updates)


def get_moisture_status(moisture_level):
    """Get moisture status and styling"""
    if moisture_level >= 60:
        return "Optimal", "status-wet", "#27ae60"
    elif moisture_level >= 40:
        return "Moderate", "status-active", "#f39c12"
    else:
        return "Dry", "status-critical", "#e74c3c"