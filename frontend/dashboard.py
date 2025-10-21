import streamlit as st
import requests
import time
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_TIMEOUT = 30
MAX_RETRIES = 3

# Modern CSS with enhanced styling
st.markdown("""
<style>
    .main { background-color: #f8f9fa; max-width: 100%; padding: 0; font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
    .main-header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem 2rem; box-shadow: 0 4px 20px rgba(0,0,0,0.1); position: sticky; top: 0; z-index: 1000; }
    .auth-container { display: flex; justify-content: center; align-items: center; min-height: 100vh; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 2rem; }
    .auth-card { background: white; border-radius: 20px; padding: 3rem; box-shadow: 0 20px 60px rgba(0,0,0,0.15); width: 100%; max-width: 450px; margin: 0 auto; }
    .dashboard-card { background: white; border-radius: 16px; padding: 1.5rem; margin-bottom: 1.5rem; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid #e9ecef; height: 100%; transition: all 0.3s ease; }
    .dashboard-card:hover { transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0,0,0,0.15); }
    .card-header { font-size: 1.1rem; font-weight: 700; color: #2c3e50; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 3px solid #667eea; display: flex; align-items: center; gap: 0.5rem; }
    .metric-card { background: white; border-radius: 16px; padding: 1.5rem; text-align: center; box-shadow: 0 4px 20px rgba(0,0,0,0.08); border-left: 5px solid #667eea; height: 100%; transition: all 0.3s ease; }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 12px 40px rgba(0,0,0,0.15); }
    .metric-card.moisture { border-left-color: #3498db; }
    .metric-card.warning { border-left-color: #f39c12; }
    .metric-card.critical { border-left-color: #e74c3c; }
    .metric-card.success { border-left-color: #27ae60; }
    .metric-value { font-size: 2.5rem; font-weight: 800; color: #2c3e50; margin: 0.5rem 0; }
    .metric-label { font-size: 0.9rem; color: #7f8c8d; text-transform: uppercase; letter-spacing: 1px; font-weight: 700; }
    .metric-unit { font-size: 0.8rem; color: #95a5a6; margin-top: 0.25rem; font-weight: 600; }
    .status-badge { display: inline-flex; align-items: center; padding: 8px 16px; border-radius: 25px; font-size: 0.8rem; font-weight: 700; margin: 2px; gap: 6px; }
    .status-active { background: #667eea; color: white; }
    .status-wet { background: #27ae60; color: white; }
    .status-dry { background: #f39c12; color: white; }
    .status-critical { background: #e74c3c; color: white; }
    .status-standby { background: #95a5a6; color: white; }
    .progress-container { background: #ecf0f1; border-radius: 15px; height: 12px; overflow: hidden; margin: 12px 0; box-shadow: inset 0 2px 4px rgba(0,0,0,0.1); }
    .progress-bar { height: 100%; border-radius: 15px; transition: width 0.5s ease; box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
    .progress-moisture { background: #3498db; }
    .progress-warning { background: #f39c12; }
    .progress-critical { background: #e74c3c; }
    .auth-btn { background: linear-gradient(135deg, #667eea, #764ba2); color: white; border: none; padding: 16px 32px; border-radius: 12px; font-weight: 700; cursor: pointer; transition: all 0.3s ease; width: 100%; font-size: 1.1rem; margin-top: 1rem; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.4); }
    .auth-btn:hover { background: linear-gradient(135deg, #5a6fd8, #6a42a0); transform: translateY(-3px); box-shadow: 0 12px 35px rgba(102, 126, 234, 0.6); }
    .auth-btn:active { transform: translateY(-1px); }
    .secondary-btn { background: #95a5a6; color: white; border: none; padding: 14px 28px; border-radius: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s ease; width: 100%; font-size: 1rem; box-shadow: 0 6px 20px rgba(149, 165, 166, 0.4); }
    .secondary-btn:hover { background: #7f8c8d; transform: translateY(-2px); }
    .irrigation-btn { background: #667eea; color: white; border: none; padding: 14px 28px; border-radius: 12px; font-weight: 700; cursor: pointer; transition: all 0.3s ease; width: 100%; font-size: 1rem; box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }
    .irrigation-btn:hover { background: #5a6fd8; transform: translateY(-3px); box-shadow: 0 10px 30px rgba(102, 126, 234, 0.6); }
    .alert-item { background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; border-left: 5px solid #f39c12; transition: all 0.3s ease; }
    .alert-item:hover { transform: translateX(8px); box-shadow: 0 8px 25px rgba(0,0,0,0.15); }
    .alert-critical { background: #f8d7da; border: 1px solid #f5c6cb; border-left: 5px solid #e74c3c; }
    .alert-info { background: #d1ecf1; border: 1px solid #bee5eb; border-left: 5px solid #3498db; }
    .alert-success { background: #d4efdf; border: 1px solid #c8e6c9; border-left: 5px solid #27ae60; }
    .zone-item { background: white; border: 1px solid #e9ecef; border-radius: 12px; padding: 1.2rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; transition: all 0.3s ease; }
    .zone-item:hover { border-color: #667eea; box-shadow: 0 8px 25px rgba(102, 126, 234, 0.2); transform: translateY(-2px); }
    .zone-active { border-left: 5px solid #667eea; background: #f8f9fa; }
    .form-group { margin-bottom: 1.5rem; }
    .form-label { display: block; margin-bottom: 0.5rem; font-weight: 700; color: #2c3e50; font-size: 0.95rem; }
    .form-input { width: 100%; padding: 14px 18px; border: 2px solid #e9ecef; border-radius: 12px; font-size: 1rem; transition: all 0.3s ease; background: white; }
    .form-input:focus { outline: none; border-color: #667eea; box-shadow: 0 0 0 4px rgba(102, 126, 234, 0.1); }
    .section-divider { border: none; height: 2px; background: linear-gradient(90deg, transparent, #667eea, transparent); margin: 2rem 0; }
    .sidebar .sidebar-content { background: #2c3e50; border-right: 1px solid #34495e; padding: 2rem 1rem; }
    .nav-item { display: flex; align-items: center; padding: 14px 18px; margin: 6px 0; border-radius: 12px; color: #ecf0f1; text-decoration: none; transition: all 0.3s ease; gap: 14px; font-weight: 600; }
    .nav-item:hover { background: rgba(255,255,255,0.1); color: white; transform: translateX(8px); }
    .nav-item.active { background: #667eea; color: white; border-left: 4px solid #ecf0f1; }
    @keyframes pulse { 0% { transform: scale(1); } 50% { transform: scale(1.05); } 100% { transform: scale(1); } }
    .pulse { animation: pulse 2s infinite; }
    .data-source-badge { background: #667eea; color: white; padding: 6px 12px; border-radius: 20px; font-size: 0.75rem; font-weight: 700; margin-left: 8px; }
    .data-source-real { background: #27ae60; }
    .data-source-sensor { background: #f39c12; }
    .error-banner { background: #f8d7da; color: #721c24; padding: 14px 18px; border-radius: 12px; border: 1px solid #f5c6cb; margin-bottom: 1rem; }
    .success-banner { background: #d4edda; color: #155724; padding: 14px 18px; border-radius: 12px; border: 1px solid #c3e6cb; margin-bottom: 1rem; }
    .forgot-password-link { color: #667eea; text-decoration: none; font-weight: 600; transition: all 0.3s ease; }
    .forgot-password-link:hover { color: #764ba2; text-decoration: underline; }
    .auth-footer { text-align: center; margin-top: 2rem; padding-top: 1.5rem; border-top: 1px solid #e9ecef; }
    .welcome-animation { animation: slideInUp 0.8s ease; }
    @keyframes slideInUp { from { transform: translateY(30px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
   
    /* Fix for sidebar text colors */
    .sidebar .sidebar-content * { color: #ecf0f1 !important; }
    .sidebar .sidebar-content .css-1d391kg p { color: #ecf0f1 !important; }
   
    /* Fix for metric values */
    .metric-value { color: #2c3e50 !important; }
   
    @media (max-width: 768px) {
        .auth-card { padding: 2rem; margin: 1rem; }
        .main-header { padding: 1rem; }
        .dashboard-card { padding: 1rem; }
        .metric-value { font-size: 2rem; }
    }
    div.stButton > button:first-child {
        background-color: green;
        color: white;
        border: none;
    }
    div.stButton > button:first-child:hover {
        background-color: darkgreen;
        color: white;
    }
    
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'auth' not in st.session_state:
    st.session_state.auth = {
        'authenticated': False,
        'token': None,
        'refresh_token': None,
        'show_register': False,
        'show_forgot_password': False,
        'user': None,
        'last_refresh': None,
        'remember_me': False,
        'current_page': 'dashboard',
        'data': {},
        'data_refresh_status': {
            'last_refresh': None,
            'in_progress': False,
            'last_success': None
        },
        'api_errors': []
    }


def log_error(error_type: str, error_message: str):
    error_entry = {
        'timestamp': datetime.now().isoformat(),
        'type': error_type,
        'message': error_message
    }
    st.session_state.auth['api_errors'].append(error_entry)
    if len(st.session_state.auth['api_errors']) > 10:
        st.session_state.auth['api_errors'] = st.session_state.auth['api_errors'][-10:]


def make_api_request(url: str, method: str = "GET", data: dict = None, headers: dict = None, retry_count: int = 0):
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=API_TIMEOUT)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=API_TIMEOUT)
        else:
            return None

        return response
    except requests.exceptions.Timeout:
        if retry_count < MAX_RETRIES:
            time.sleep(1)
            return make_api_request(url, method, data, headers, retry_count + 1)
        log_error("timeout", f"Request timeout after {MAX_RETRIES} retries: {url}")
        return None
    except requests.exceptions.ConnectionError:
        log_error("connection", f"Cannot connect to API: {url}")
        return None
    except requests.exceptions.RequestException as e:
        log_error("request", f"Request failed: {str(e)}")
        return None


def is_valid_email(email: str) -> bool:
    import re
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> dict:
    if len(password) < 8:
        return {"valid": False, "message": "Password must be at least 8 characters long"}

    if not any(char.isdigit() for char in password):
        return {"valid": False, "message": "Password must contain at least one digit"}

    if not any(char.isupper() for char in password):
        return {"valid": False, "message": "Password must contain at least one uppercase letter"}

    if not any(char.islower() for char in password):
        return {"valid": False, "message": "Password must contain at least one lowercase letter"}

    if not any(char in '!@#$%^&*(),.?":{}|<>' for char in password):
        return {"valid": False, "message": "Password must contain at least one special character"}

    return {"valid": True, "message": "Password is strong"}


def register_user(user_data: dict) -> tuple:
    try:
        with st.spinner("Creating your account..."):
            response = make_api_request(
                f"{API_BASE_URL}/auth/register",
                method="POST",
                data=user_data
            )

        if response and response.status_code in [200, 201]:
            return True, "Registration successful! Please login."
        else:
            error_detail = "Registration failed"
            if response:
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', error_detail)
                except:
                    error_detail = f"HTTP {response.status_code}: {response.text}"
            log_error("registration", error_detail)
            return False, error_detail
    except Exception as e:
        error_msg = f"Registration error: {str(e)}"
        log_error("registration", error_msg)
        return False, error_msg


def login_user(username: str, password: str, remember_me: bool = False) -> tuple:
    try:
        with st.spinner("Signing you in..."):
            data = {
                "username": username,
                "password": password,
                "remember_me": remember_me
            }

            response = requests.post(
                f"{API_BASE_URL}/auth/login",
                json=data,
                timeout=API_TIMEOUT
            )

        if response and response.status_code == 200:
            token_data = response.json()
            st.session_state.auth['token'] = token_data['access_token']
            st.session_state.auth['refresh_token'] = token_data['refresh_token']
            st.session_state.auth['authenticated'] = True
            st.session_state.auth['last_refresh'] = datetime.now()
            st.session_state.auth['remember_me'] = remember_me

            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            user_response = requests.get(
                f"{API_BASE_URL}/auth/users/me",
                headers=headers,
                timeout=API_TIMEOUT
            )

            if user_response and user_response.status_code == 200:
                st.session_state.auth['user'] = user_response.json()
            else:
                st.session_state.auth['user'] = {
                    'username': username,
                    'email': 'user@example.com',
                    'full_name': 'User'
                }

            return True, "Login successful!"
        else:
            error_detail = "Invalid username or password"
            if response:
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', error_detail)
                except:
                    error_detail = f"HTTP {response.status_code}: {response.text}"
            log_error("login", error_detail)
            return False, error_detail
    except Exception as e:
        error_msg = f"Login error: {str(e)}"
        log_error("login", error_msg)
        return False, error_msg


def handle_forgot_password(email: str) -> tuple:
    try:
        with st.spinner("Sending reset instructions..."):
            response = requests.post(
                f"{API_BASE_URL}/auth/forgot-password",
                json={"email": email},
                timeout=API_TIMEOUT
            )

        if response and response.status_code == 200:
            return True, "If the email exists, a password reset link has been sent"
        else:
            error_detail = "Failed to send reset instructions"
            if response:
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', error_detail)
                except:
                    error_detail = f"HTTP {response.status_code}: {response.text}"
            return False, error_detail
    except Exception as e:
        return False, f"Error: {str(e)}"


def handle_password_reset(token: str, new_password: str, confirm_password: str) -> tuple:
    if new_password != confirm_password:
        return False, "Passwords do not match"

    password_validation = validate_password_strength(new_password)
    if not password_validation["valid"]:
        return False, password_validation["message"]

    try:
        with st.spinner("Resetting password..."):
            response = requests.post(
                f"{API_BASE_URL}/auth/reset-password",
                json={
                    "token": token,
                    "new_password": new_password
                },
                timeout=API_TIMEOUT
            )

        if response and response.status_code == 200:
            return True, "Password has been reset successfully"
        else:
            error_detail = "Failed to reset password"
            if response:
                try:
                    error_data = response.json()
                    error_detail = error_data.get('detail', error_detail)
                except:
                    error_detail = f"HTTP {response.status_code}: {response.text}"
            return False, error_detail
    except Exception as e:
        return False, f"Error: {str(e)}"


def validate_reset_token(token: str) -> tuple:
    try:
        response = requests.post(
            f"{API_BASE_URL}/auth/validate-reset-token",
            data={"token": token},
            timeout=API_TIMEOUT
        )

        if response and response.status_code == 200:
            return True, "Token is valid"
        else:
            return False, "Invalid or expired reset token"
    except Exception as e:
        return False, f"Error validating token: {str(e)}"


def get_current_user_info():
    try:
        headers = {"Authorization": f"Bearer {st.session_state.auth['token']}"}
        response = make_api_request(f"{API_BASE_URL}/auth/users/me", headers=headers)
        if response and response.status_code == 200:
            return response.json()
    except Exception as e:
        log_error("user_info", f"Failed to get user info: {str(e)}")
    return None


def make_authenticated_request(endpoint: str, method: str = "GET", data: dict = None):
    if not st.session_state.auth.get('token'):
        st.error("Not authenticated. Please login again.")
        st.session_state.auth['authenticated'] = False
        return None

    headers = {"Authorization": f"Bearer {st.session_state.auth['token']}"}

    try:
        url = f"{API_BASE_URL}{endpoint}"
        response = make_api_request(url, method, data, headers)

        if response and response.status_code == 401:
            st.session_state.auth['authenticated'] = False
            st.session_state.auth['token'] = None
            st.error("Session expired. Please login again.")
            st.rerun()

        return response
    except Exception as e:
        log_error("auth_request", f"Authenticated request failed: {str(e)}")
        return None


def refresh_dashboard_data():
    try:
        response = make_authenticated_request("/api/dashboard-data")
        if response and response.status_code == 200:
            st.session_state.auth['data'] = response.json()
            st.session_state.auth['last_refresh'] = datetime.now()
            return True
        else:
            error_msg = "Failed to refresh dashboard data"
            if response:
                error_msg += f" (HTTP {response.status_code})"
            log_error("dashboard_refresh", error_msg)
            return False
    except Exception as e:
        error_msg = f"Error refreshing dashboard data: {str(e)}"
        log_error("dashboard_refresh", error_msg)
        return False


def get_data_refresh_status():
    try:
        response = make_authenticated_request("/api/data/status")
        if response and response.status_code == 200:
            status_data = response.json()
            st.session_state.auth['data_refresh_status'] = status_data
            return status_data
        return None
    except Exception as e:
        log_error("status_check", f"Failed to get data status: {str(e)}")
        return None


def start_irrigation(zone: str, duration: int):
    try:
        response = make_authenticated_request("/api/control/irrigate", method="POST", data={
            "zone": zone,
            "duration": duration
        })
        if response and response.status_code == 200:
            return True, "Irrigation started successfully!"
        else:
            error_msg = "Failed to start irrigation"
            if response:
                error_msg += f" (HTTP {response.status_code})"
            log_error("irrigation", error_msg)
            return False, error_msg
    except Exception as e:
        error_msg = f"Error starting irrigation: {str(e)}"
        log_error("irrigation", error_msg)
        return False, error_msg


def get_alerts():
    try:
        response = make_authenticated_request("/api/data/alerts?acknowledged=false")
        if response and response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        log_error("alerts", f"Failed to get alerts: {str(e)}")
        return []


def acknowledge_alert(alert_id: int):
    try:
        response = make_authenticated_request(f"/api/alerts/{alert_id}/acknowledge", method="POST")
        return response and response.status_code == 200
    except Exception as e:
        log_error("alert_ack", f"Failed to acknowledge alert {alert_id}: {str(e)}")
        return False


def get_sensor_data():
    try:
        response = make_authenticated_request("/api/data/readings?hours=24")
        if response and response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        log_error("sensor_data", f"Failed to get sensor data: {str(e)}")
        return []


def get_historical_data(days: int = 7):
    try:
        response = make_authenticated_request(f"/api/historical-data/{days}")
        if response and response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                return data
        return []
    except Exception as e:
        log_error("historical_data", f"Failed to get historical data: {str(e)}")
        return []


def get_system_settings():
    try:
        response = make_authenticated_request("/api/system/settings")
        if response and response.status_code == 200:
            return response.json().get('settings', {})
        return {}
    except Exception as e:
        log_error("settings", f"Failed to get system settings: {str(e)}")
        return {}


def update_system_setting(setting_key: str, setting_value: str):
    try:
        response = make_authenticated_request(f"/api/system/settings/{setting_key}", method="PUT", data={
            "setting_value": setting_value
        })
        return response and response.status_code == 200
    except Exception as e:
        log_error("settings_update", f"Failed to update setting {setting_key}: {str(e)}")
        return False


def get_moisture_status(moisture_level: float) -> tuple:
    if moisture_level >= 60:
        return "Optimal", "status-wet", "#27ae60"
    elif moisture_level >= 40:
        return "Moderate", "status-active", "#f39c12"
    else:
        return "Dry", "status-critical", "#e74c3c"


def create_moisture_gauge(value, zone_name):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={'suffix': "%", 'font': {'size': 24}},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "#3498db"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 30], 'color': '#f8d7da'},
                {'range': [30, 60], 'color': '#fff3cd'},
                {'range': [60, 100], 'color': '#d1ecf1'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        },
        title={'text': f"Zone {zone_name[-1]}", 'font': {'size': 16}}
    ))

    fig.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'color': "#2c3e50"}
    )
    return fig


def create_historical_chart():
    try:
        historical_data = get_historical_data(7)

        if historical_data:
            df = pd.DataFrame(historical_data)

            if 'date' in df.columns and 'avg_moisture' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.sort_values('date')

                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=df['date'],
                    y=df['avg_moisture'],
                    mode='lines+markers',
                    line=dict(color='#3498db', width=3),
                    marker=dict(size=6, color='#2980b9'),
                    name='Soil Moisture',
                    fill='tozeroy',
                    fillcolor='rgba(52, 152, 219, 0.1)'
                ))

                fig.add_hrect(y0=60, y1=100, fillcolor="green", opacity=0.1, line_width=0, annotation_text="Optimal")
                fig.add_hrect(y0=40, y1=60, fillcolor="yellow", opacity=0.1, line_width=0, annotation_text="Moderate")
                fig.add_hrect(y0=0, y1=40, fillcolor="red", opacity=0.1, line_width=0, annotation_text="Dry")

                fig.update_layout(
                    title="7-Day Soil Moisture Trends",
                    xaxis_title="Date",
                    yaxis_title="Moisture Level (%)",
                    height=300,
                    margin=dict(l=20, r=20, t=40, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False
                )
                return fig
        else:
            return None
    except Exception as e:
        log_error("chart", f"Error creating historical chart: {str(e)}")
        return None


def create_zone_chart(zone_data, title):
    try:
        pivot_df = zone_data.pivot_table(
            index='timestamp',
            columns='sensor_type',
            values='value',
            aggfunc='mean'
        ).reset_index()

        fig = go.Figure()

        colors = {
            'soil': '#3498db',
            'temp': '#e74c3c',
            'humidity': '#2980b9',
            'light': '#f39c12'
        }

        for sensor_type in pivot_df.columns:
            if sensor_type != 'timestamp' and sensor_type in colors:
                y_data = pivot_df[sensor_type] * 100 if sensor_type == 'soil' else pivot_df[sensor_type]

                fig.add_trace(go.Scatter(
                    x=pivot_df['timestamp'],
                    y=y_data,
                    mode='lines+markers',
                    name=sensor_type.upper(),
                    line=dict(color=colors[sensor_type], width=2),
                    marker=dict(size=4)
                ))

        fig.update_layout(
            title=title,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            xaxis_title="Time",
            yaxis_title="Value"
        )

        return fig

    except Exception as e:
        log_error("zone_chart", f"Error creating zone chart: {str(e)}")
        return go.Figure()


def render_auth_page():
    query_params = st.query_params
    reset_token = query_params.get("token", [None])[0]

    if reset_token:
        render_reset_password_page(reset_token)
        return

    if st.session_state.auth['show_forgot_password']:
        render_forgot_password_page()
        return

    if st.session_state.auth['show_register']:
        render_register_page()
    else:
        render_login_page()


def render_login_page():
    st.markdown("""
        <div class="welcome-animation">
            <div style="text-align: center; margin-bottom: 2rem;">
                <h1 style="color:#27ae60; margin-bottom:0.5rem; font-size: 2.5rem;">🌱 Smart Irrigation</h1>
                <h3 style="color:#7f8c8d; font-weight:400; margin-bottom: 2rem;">Growing Smarter, Not Harder</h3>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        col1, col2 = st.columns([2, 1])
        with col1:
            username = st.text_input("👤 Username", placeholder="Enter your username")
        with col2:
            st.markdown('<div style="height: 32px;"></div>', unsafe_allow_html=True)
            remember_me = st.checkbox("Remember me", value=st.session_state.auth.get('remember_me', False))

        password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")

        # Forgot password and login button in same row
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.form_submit_button("Forgot Password?", use_container_width=True, type="secondary"):
                st.session_state.auth['show_forgot_password'] = True
                st.rerun()
        with col2:
            login_submitted = st.form_submit_button("Sign In", use_container_width=True)

        if login_submitted:
            if not username or not password:
                st.error("Please enter both username and password")
            else:
                success, message = login_user(username, password, remember_me)
                if success:
                    st.success(message)
                    refresh_dashboard_data()
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(message)

    st.markdown("""
        <div class="auth-footer">
            <p style="color: #7f8c8d; margin-bottom: 1rem;">Don't have an account?</p>
        </div>
    """, unsafe_allow_html=True)

    if st.button("Create Account", use_container_width=True, type="primary"):
        st.session_state.auth['show_register'] = True
        st.rerun()


def render_forgot_password_page():
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color:#2c3e50; margin-bottom:0.5rem;">Reset Your Password</h2>
            <p style="color:#7f8c8d;">Enter your email to receive reset instructions</p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("forgot_password_form"):
        email = st.text_input("📧 Email Address", placeholder="Enter your registered email")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.form_submit_button("⬅️ Back to Login", use_container_width=True, type="secondary"):
                st.session_state.auth['show_forgot_password'] = False
                st.rerun()
        with col2:
            submitted = st.form_submit_button("📨 Send Reset Link", use_container_width=True)

        if submitted:
            if not email:
                st.error("Please enter your email address")
            elif not is_valid_email(email):
                st.error("Please enter a valid email address")
            else:
                success, message = handle_forgot_password(email)
                if success:
                    st.success(message)
                    time.sleep(2)
                    st.session_state.auth['show_forgot_password'] = False
                    st.rerun()
                else:
                    st.error(message)


def render_register_page():
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color:#2c3e50; margin-bottom:0.5rem;">Create Your Account</h2>
            <p style="color:#7f8c8d;">Join our smart irrigation platform</p>
        </div>
    """, unsafe_allow_html=True)

    with st.form("register_form"):
        full_name = st.text_input("👤 Full Name", placeholder="Enter your full name")
        username = st.text_input("🪪 Username", placeholder="Choose a username")
        email = st.text_input("📧 Email", placeholder="Enter your email")
        password = st.text_input("🔒 Password", type="password", placeholder="Create a strong password")
        confirm_password = st.text_input("✅ Confirm Password", type="password", placeholder="Confirm your password")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.form_submit_button("⬅️ Back to Login", use_container_width=True, type="secondary"):
                st.session_state.auth['show_register'] = False
                st.rerun()
        with col2:
            submitted = st.form_submit_button("Create Account", use_container_width=True)

        if submitted:
            if not all([username, email, full_name, password, confirm_password]):
                st.error("Please fill in all fields")
            elif not is_valid_email(email):
                st.error("Please enter a valid email address")
            elif password != confirm_password:
                st.error("Passwords do not match")
            else:
                password_validation = validate_password_strength(password)
                if not password_validation["valid"]:
                    st.error(password_validation["message"])
                else:
                    success, message = register_user({
                        "full_name": full_name,
                        "username": username,
                        "email": email,
                        "password": password
                    })
                    if success:
                        st.success(message)
                        st.session_state.auth['show_register'] = False
                        st.rerun()
                    else:
                        st.error(message)


def render_reset_password_page(token: str):
    st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h2 style="color:#2c3e50; margin-bottom:0.5rem;">🔄 Reset Your Password</h2>
            <p style="color:#7f8c8d;">Create a new secure password</p>
        </div>
    """, unsafe_allow_html=True)

    is_valid, message = validate_reset_token(token)

    if not is_valid:
        st.error(message)
        st.markdown('<div style="text-align: center; margin-top: 1.5rem;">', unsafe_allow_html=True)
        if st.button("⬅️ Back to Login", use_container_width=True):
            st.query_params.clear()
            st.session_state.auth['show_register'] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        return

    with st.form("reset_password_form"):
        new_password = st.text_input("🔒 New Password", type="password", placeholder="Enter new password")
        confirm_password = st.text_input("✅ Confirm Password", type="password", placeholder="Confirm new password")

        submitted = st.form_submit_button("🔄 Reset Password", use_container_width=True)

        if submitted:
            if not new_password or not confirm_password:
                st.error("Please fill in all fields")
            else:
                success, message = handle_password_reset(token, new_password, confirm_password)
                if success:
                    st.success(message)
                    time.sleep(2)
                    st.query_params.clear()
                    st.session_state.auth['show_register'] = False
                    st.rerun()
                else:
                    st.error(message)

    st.markdown('<div style="text-align: center; margin-top: 1.5rem;">', unsafe_allow_html=True)
    if st.button("⬅️ Back to Login", use_container_width=True, type="secondary"):
        st.query_params.clear()
        st.session_state.auth['show_register'] = False
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def render_sidebar():
    with st.sidebar:
        st.markdown("""
            <div style="text-align: center; margin-bottom: 2rem; padding: 1rem;">
                <h2 style="color: green; margin-bottom: 0.5rem; font-size: 1.5rem;">🌱</h2>
                <p style="color: #27ae60; font-size: 0.9rem; margin-bottom: 0.5rem;">Smart Irrigation</p>
                <div style="background: #27ae60; padding: 4px 12px; border-radius: 20px; display: inline-block;">
                    <p style="color: white; font-size: 0.7rem; font-weight: 700; margin: 0;">LIVE</p>
                </div>
            </div>
        """, unsafe_allow_html=True)

        pages = [
            {"icon": "📊", "name": "Dashboard", "key": "dashboard"},
            {"icon": "🌡️", "name": "Sensor Data", "key": "sensors"},
            {"icon": "🚰", "name": "Irrigation", "key": "irrigation"},
            {"icon": "📈", "name": "Analytics", "key": "analytics"},
            {"icon": "⚠️", "name": "Alerts", "key": "alerts"},
            {"icon": "⚙️", "name": "Settings", "key": "settings"}
        ]

        for page in pages:
            is_active = st.session_state.auth['current_page'] == page['key']
            if st.button(f"{page['icon']} {page['name']}",
                         key=f"nav_{page['key']}",
                         use_container_width=True,
                         type="primary" if is_active else "secondary"):
                st.session_state.auth['current_page'] = page['key']
                st.rerun()

        st.markdown(
            """<div style="margin-top: 2rem;"><hr style="margin: 1rem 0; border-color: rgba(255,255,255,0.1);"></div>""",
            unsafe_allow_html=True)

        refresh_status = st.session_state.auth.get('data_refresh_status', {})
        last_success = refresh_status.get('last_success')
        in_progress = refresh_status.get('in_progress', False)

        if last_success:
            try:
                last_refresh_time = datetime.fromisoformat(last_success.replace('Z', '+00:00'))
                time_ago = datetime.now() - last_refresh_time
                hours_ago = time_ago.total_seconds() / 3600

                if hours_ago < 1:
                    status_text = "Just now"
                    status_color = "#27ae60"
                elif hours_ago < 24:
                    status_text = f"{int(hours_ago)}h ago"
                    status_color = "#f39c12"
                else:
                    status_text = f"{int(hours_ago / 24)}d ago"
                    status_color = "#e74c3c"
            except:
                status_text = "Unknown"
                status_color = "#95a5a6"
        else:
            status_text = "Never"
            status_color = "#e74c3c"

        st.markdown(f"""
                   <div style="background: rgba(255,255,255,0.1); padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
                       <div style="font-size: 0.8rem; color: #bdc3c7; margin-bottom: 0.5rem;">Data Status</div>
                       <div style="display: flex; justify-content: space-between; align-items: center;">
                           <span style="color: #27ae60; font-size: 0.8rem; font-weight: 600;">Last Update</span>
                           <span style="color: #27ae60; font-size: 0.8rem; font-weight: 450;">Just now</span>
                       </div>
                   </div>
               """, unsafe_allow_html=True)

        if st.button("🔄 Refresh Data", use_container_width=True):
            if refresh_dashboard_data():
                st.success("Dashboard refreshed!")
            st.rerun()

        last_refresh = st.session_state.auth.get('last_refresh')
        if last_refresh:
            st.caption(f"Last update: {last_refresh.strftime('%H:%M:%S')}")

        if st.button("🚪 Logout", use_container_width=True, type="secondary"):
            st.session_state.auth['authenticated'] = False
            st.session_state.auth['token'] = None
            st.session_state.auth['user'] = None
            st.session_state.auth['data'] = {}
            st.rerun()


def render_header():
    user = st.session_state.auth.get('user', {})
    username = user.get('username', 'User') if user else 'User'

    data = st.session_state.auth.get('data', {})
    data_source = data.get('data_source', 'sensor')
    data_source_text = "Live" if data_source == 'real_world' else "Sensor"
    data_source_class = "data-source-real" if data_source == 'real_world' else "data-source-sensor"

    st.markdown(f"""
    <div class="main-header">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <h1 style="margin: 0; font-size: 2rem; color: white; font-weight: 800;">🌱 Smart Irrigation System</h1>
                <p style="margin: 0; color: rgba(255,255,255,0.9); font-size: 1.1rem;">
                    Real-time Monitoring & Analytics
                    <span class="data-source-badge {data_source_class}">{data_source_text} Data</span>
                </p>
            </div>
            <div style="display: flex; align-items: center; gap: 1rem;">
                <div style="background: rgba(255,255,255,0.2); padding: 0.75rem 1.5rem; border-radius: 25px; backdrop-filter: blur(10px);">
                    <span style="color: white; font-weight: 600;">👤 {username}</span>
                </div>
                <div style="color: #27ae60; font-weight: 800; background: rgba(39, 174, 96, 0.2); padding: 0.5rem 1rem; border-radius: 20px;">● Live</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_dashboard():
    """Render main dashboard - uses REAL API data only"""
    render_header()

    # Refresh data if needed
    if (not st.session_state.auth.get('last_refresh') or
            (datetime.now() - st.session_state.auth['last_refresh']).seconds > 30):
        with st.spinner("Refreshing data..."):
            refresh_dashboard_data()
            get_data_refresh_status()

    data = st.session_state.auth.get('data', {})

    # Show data source info
    data_source = data.get('data_source', 'sensor')

    # System Overview Cards
    st.markdown('<h2 style="margin: 2rem 0 1rem 0; color: #2c3e50;">System Overview</h2>', unsafe_allow_html=True)

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Get water usage from the new water_usage field
        water_usage_data = data.get('water_usage', {})
        water_used = water_usage_data.get('today_water_used', 0)
        st.markdown(f"""
            <div class="metric-card moisture">
                <div class="metric-label">Water Usage</div>
                <div class="metric-value">{water_used:.1f}</div>
                <div class="metric-unit">liters</div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        # Show irrigation events count
        irrigation_events = water_usage_data.get('total_irrigation_events', 0)
        st.markdown(f"""
            <div class="metric-card success">
                <div class="metric-label">Irrig. Events</div>
                <div class="metric-value">{irrigation_events}</div>
                <div class="metric-unit">today</div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        zones_active = data.get('system_metrics', {}).get('zones_active', 0)
        st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Active Zones</div>
                <div class="metric-value">{zones_active}</div>
                <div class="metric-unit">of 2</div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        uptime = data.get('system_metrics', {}).get('uptime', 0)
        st.markdown(f"""
            <div class="metric-card success">
                <div class="metric-label">System Uptime</div>
                <div class="metric-value">{uptime:.1f}</div>
                <div class="metric-unit">%</div>
            </div>
        """, unsafe_allow_html=True)

    # Soil Moisture Section
    st.markdown('<h3 style="margin: 2rem 0 1rem 0; color: #2c3e50;">Soil Moisture Levels</h3>', unsafe_allow_html=True)

    soil_moisture = data.get('soil_moisture', {})
    irrigation_status = data.get('irrigation_status', {})

    col1, col2 = st.columns(2)

    # Handle different zone names (field_1, zone1, etc.)
    zone1_key = next((key for key in ['zone1', 'field_1'] if key in soil_moisture), 'zone1')
    zone2_key = next((key for key in ['zone2', 'field_2'] if key in soil_moisture), 'zone2')

    with col1:
        zone1_moisture = soil_moisture.get(zone1_key, 0)
        status_text, status_class, status_color = get_moisture_status(zone1_moisture)
        needs_water = irrigation_status.get(zone1_key, False)

        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">🌿 Zone 1 - Vegetable Garden</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <span class="metric-value" style="color: {status_color};">{zone1_moisture:.1f}%</span>
                    <span class="status-badge {status_class}">{status_text}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar progress-moisture" style="width: {min(zone1_moisture, 100)}%;"></div>
                </div>
                <div style="margin-top: 1rem; display: flex; justify-content: space-between;">
                    <span style="font-size: 0.8rem; color: #7f8c8d;">Dry</span>
                    <span style="font-size: 0.8rem; color: #7f8c8d;">Optimal</span>
                </div>
                <div style="margin-top: 1rem; text-align: center;">
                    <span class="status-badge {'status-critical' if needs_water else 'status-success'}">
                        {'🚰 Needs Water' if needs_water else 'Soil Moisture'}
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        zone2_moisture = soil_moisture.get(zone2_key, 0)
        status_text, status_class, status_color = get_moisture_status(zone2_moisture)
        needs_water = irrigation_status.get(zone2_key, False)

        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">🌻 Zone 2 - Flower Beds</div>
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                    <span class="metric-value" style="color: {status_color};">{zone2_moisture:.1f}%</span>
                    <span class="status-badge {status_class}">{status_text}</span>
                </div>
                <div class="progress-container">
                    <div class="progress-bar progress-moisture" style="width: {min(zone2_moisture, 100)}%;"></div>
                </div>
                <div style="margin-top: 1rem; display: flex; justify-content: space-between;">
                    <span style="font-size: 0.8rem; color: #7f8c8d;">Dry</span>
                    <span style="font-size: 0.8rem; color: #7f8c8d;">Optimal</span>
                </div>
                <div style="margin-top: 1rem; text-align: center;">
                    <span class="status-badge {'status-critical' if needs_water else 'status-success'}">
                        {'🚰 Needs Water' if needs_water else 'Soil Moisture'}
                    </span>
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Environmental Conditions
    col1, col2, col3 = st.columns(3)

    with col1:
        weather = data.get('weather', {})
        temp = weather.get('temperature', 0)
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">🌡️ Temperature</div>
                <div class="metric-value" style="color: #e74c3c;">{temp:.1f}°C</div>
                <div style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem;">
                    {weather.get('forecast', 'Live sensor data')}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        humidity = weather.get('humidity', 0)
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">💧 Humidity</div>
                <div class="metric-value" style="color: #3498db;">{humidity:.1f}%</div>
                <div style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem;">
                    Current ambient humidity
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        light_level = data.get('light_level', 0)
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">☀️ Light Level</div>
                <div class="metric-value" style="color: #f39c12;">{light_level:.1f}</div>
                <div style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem;">
                    Light intensity level
                </div>
            </div>
        """, unsafe_allow_html=True)

    # Charts and Historical Data
    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown('<div class="dashboard-card"><div class="card-header">📈 Soil Moisture Trends</div>',
                    unsafe_allow_html=True)
        chart = create_historical_chart()
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.info("No historical data available yet. Data will appear after system collects real measurements.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="dashboard-card"><div class="card-header">⚠️ Recent Alerts</div>',
                    unsafe_allow_html=True)
        alerts = data.get('alerts', [])
        if alerts:
            for alert in alerts[:5]:
                alert_class = "alert-critical" if alert.get('critical') else "alert-info"
                st.markdown(f"""
                    <div class="alert-item {alert_class}">
                        <div style="font-weight: 600; margin-bottom: 0.25rem;">{alert.get('message', 'Alert')}</div>
                        <div style="font-size: 0.8rem; color: #7f8c8d;">{alert.get('time', '')}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div style="text-align: center; padding: 2rem; color: #7f8c8d;">
                    <div style="font-size: 3rem; margin-bottom: 1rem;">✅</div>
                    <div>No active alerts</div>
                    <div style="font-size: 0.8rem;">All systems normal</div>
                </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


def render_sensor_data():
    """Render sensor data page"""
    render_header()

    st.markdown('<h2 style="margin: 2rem 0 1rem 0; color: #2c3e50;">Sensor Data</h2>', unsafe_allow_html=True)

    # Get sensor data from API
    with st.spinner("Loading sensor data..."):
        sensor_data = get_sensor_data()

    if sensor_data:
        # Convert to DataFrame for display
        df = pd.DataFrame(sensor_data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp', ascending=False)

        # Filter only Zone 1 and Zone 2
        df = df[df['zone'].isin(['zone1', 'zone2'])]

        # Display latest readings in 2 columns
        st.markdown('<h3 style="margin: 1.5rem 0 1rem 0; color: #2c3e50;">Latest Readings</h3>', unsafe_allow_html=True)

        # Create two columns for Zone 1 and Zone 2
        col1, col2 = st.columns(2)

        # Zone 1 data
        with col1:
            st.markdown('<div class="dashboard-card"><div class="card-header">🌿 Zone 1 - Vegetable Garden</div>',
                        unsafe_allow_html=True)

            zone1_data = df[df['zone'] == 'zone1']
            if not zone1_data.empty:
                # Group by sensor type and get latest reading
                latest_zone1 = zone1_data.groupby('sensor_type').first().reset_index()

                sensor_types = {
                    'soil': {'name': 'Soil Moisture', 'unit': '%', 'icon': '🌱', 'color': '#3498db'},
                    'temp': {'name': 'Temperature', 'unit': '°C', 'icon': '🌡️', 'color': '#e74c3c'},
                    'light': {'name': 'Light Level', 'unit': 'lux', 'icon': '☀️', 'color': '#f39c12'},
                    'humidity': {'name': 'Humidity', 'unit': '%', 'icon': '💧', 'color': '#2980b9'}
                }

                for _, reading in latest_zone1.iterrows():
                    sensor_type = reading['sensor_type']
                    if sensor_type in sensor_types:
                        info = sensor_types[sensor_type]
                        value = reading['value'] * 100 if sensor_type == 'soil' else reading['value']

                        st.markdown(f"""
                            <div style="margin-bottom: 1.5rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid {info['color']};">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                    <span style="font-weight: 600; color: #2c3e50;">{info['icon']} {info['name']}</span>
                                    <span style="font-size: 1.2rem; font-weight: 700; color: {info['color']};">{value:.1f}{info['unit']}</span>
                                </div>
                                <div style="color: #7f8c8d; font-size: 0.8rem;">
                                    {reading['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="text-align: center; padding: 2rem; color: #7f8c8d;">
                        <div style="font-size: 2rem; margin-bottom: 1rem;">📡</div>
                        <div>No data available for Zone 1</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        # Zone 2 data
        with col2:
            st.markdown('<div class="dashboard-card"><div class="card-header">🌻 Zone 2 - Flower Beds</div>',
                        unsafe_allow_html=True)

            zone2_data = df[df['zone'] == 'zone2']
            if not zone2_data.empty:
                # Group by sensor type and get latest reading
                latest_zone2 = zone2_data.groupby('sensor_type').first().reset_index()

                sensor_types = {
                    'soil': {'name': 'Soil Moisture', 'unit': '%', 'icon': '🌱', 'color': '#3498db'},
                    'temp': {'name': 'Temperature', 'unit': '°C', 'icon': '🌡️', 'color': '#e74c3c'},
                    'light': {'name': 'Light Level', 'unit': 'lux', 'icon': '☀️', 'color': '#f39c12'},
                    'humidity': {'name': 'Humidity', 'unit': '%', 'icon': '💧', 'color': '#2980b9'}
                }

                for _, reading in latest_zone2.iterrows():
                    sensor_type = reading['sensor_type']
                    if sensor_type in sensor_types:
                        info = sensor_types[sensor_type]
                        value = reading['value'] * 100 if sensor_type == 'soil' else reading['value']

                        st.markdown(f"""
                            <div style="margin-bottom: 1.5rem; padding: 1rem; background: #f8f9fa; border-radius: 8px; border-left: 4px solid {info['color']};">
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                                    <span style="font-weight: 600; color: #2c3e50;">{info['icon']} {info['name']}</span>
                                    <span style="font-size: 1.2rem; font-weight: 700; color: {info['color']};">{value:.1f}{info['unit']}</span>
                                </div>
                                <div style="color: #7f8c8d; font-size: 0.8rem;">
                                    {reading['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.markdown("""
                    <div style="text-align: center; padding: 2rem; color: #7f8c8d;">
                        <div style="font-size: 2rem; margin-bottom: 1rem;">📡</div>
                        <div>No data available for Zone 2</div>
                    </div>
                """, unsafe_allow_html=True)

            st.markdown('</div>', unsafe_allow_html=True)

        # Historical Charts for each zone
        st.markdown('<h3 style="margin: 2rem 0 1rem 0; color: #2c3e50;">Historical Trends</h3>', unsafe_allow_html=True)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown('<div class="dashboard-card"><div class="card-header">📈 Zone 1 Trends</div>',
                        unsafe_allow_html=True)
            if not zone1_data.empty:
                # Create chart for Zone 1
                fig_zone1 = create_zone_chart(zone1_data, "Zone 1 - Vegetable Garden")
                st.plotly_chart(fig_zone1, use_container_width=True)
            else:
                st.info("No historical data for Zone 1")
            st.markdown('</div>', unsafe_allow_html=True)

        with col2:
            st.markdown('<div class="dashboard-card"><div class="card-header">📈 Zone 2 Trends</div>',
                        unsafe_allow_html=True)
            if not zone2_data.empty:
                # Create chart for Zone 2
                fig_zone2 = create_zone_chart(zone2_data, "Zone 2 - Flower Beds")
                st.plotly_chart(fig_zone2, use_container_width=True)
            else:
                st.info("No historical data for Zone 2")
            st.markdown('</div>', unsafe_allow_html=True)

        # Raw data table (filtered for zones 1 and 2)
        st.markdown('<h3 style="margin: 1.5rem 0 1rem 0; color: #2c3e50;">Raw Sensor Data</h3>', unsafe_allow_html=True)

        # Display the filtered dataframe
        display_df = df[['timestamp', 'zone', 'sensor_type', 'value', 'source']].copy()
        display_df['value'] = display_df.apply(
            lambda x: x['value'] * 100 if x['sensor_type'] == 'soil' else x['value'],
            axis=1
        )
        display_df['value'] = display_df['value'].round(2)
        display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')

        st.dataframe(display_df.head(50), use_container_width=True)

        # Show data summary
        st.markdown(
            f"**Total readings:** {len(df)} | **Date range:** {df['timestamp'].min().strftime('%Y-%m-%d')} to {df['timestamp'].max().strftime('%Y-%m-%d')}")

    else:
        st.info("No sensor data available yet. Data will appear after the system collects real measurements from APIs.")


def create_zone_chart(zone_data, title):
    """Create a chart for a specific zone's sensor data"""
    try:
        # Pivot the data to have sensor types as columns
        pivot_df = zone_data.pivot_table(
            index='timestamp',
            columns='sensor_type',
            values='value',
            aggfunc='mean'
        ).reset_index()

        fig = go.Figure()

        # Define colors for different sensor types
        colors = {
            'soil': '#3498db',
            'temp': '#e74c3c',
            'humidity': '#2980b9',
            'light': '#f39c12'
        }

        # Add traces for each sensor type that exists in the data
        for sensor_type in pivot_df.columns:
            if sensor_type != 'timestamp' and sensor_type in colors:
                # Scale soil moisture to percentage for display
                y_data = pivot_df[sensor_type] * 100 if sensor_type == 'soil' else pivot_df[sensor_type]

                fig.add_trace(go.Scatter(
                    x=pivot_df['timestamp'],
                    y=y_data,
                    mode='lines+markers',
                    name=sensor_type.upper(),
                    line=dict(color=colors[sensor_type], width=2),
                    marker=dict(size=4)
                ))

        fig.update_layout(
            title=title,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            showlegend=True,
            xaxis_title="Time",
            yaxis_title="Value"
        )

        return fig

    except Exception as e:
        log_error("zone_chart", f"Error creating zone chart: {str(e)}")
        # Return empty figure if error
        return go.Figure()

def render_irrigation():
    """Render irrigation control page"""
    render_header()

    st.markdown('<h2 style="margin: 2rem 0 1rem 0; color: #2c3e50;">Irrigation Control</h2>', unsafe_allow_html=True)

    # Refresh data first
    if not st.session_state.auth.get('last_refresh'):
        refresh_dashboard_data()

    data = st.session_state.auth.get('data', {})
    soil_moisture = data.get('soil_moisture', {})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="dashboard-card"><div class="card-header">🚰 Zone 1 - Vegetable Garden</div>',
                    unsafe_allow_html=True)

        zone1_moisture = soil_moisture.get('zone1', 0)
        status_text, status_class, _ = get_moisture_status(zone1_moisture)

        st.markdown(f"""
            <div style="text-align: center; margin: 1rem 0;">
                <div style="font-size: 2rem; color: #2c3e50; margin-bottom: 0.5rem;">{zone1_moisture:.1f}%</div>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
        """, unsafe_allow_html=True)

        with st.form("zone1_irrigation"):
            duration = st.slider("Irrigation Duration (minutes)", 1, 30, 5, key="zone1_duration")
            if st.form_submit_button("💧 Start Irrigation", use_container_width=True):
                success, message = start_irrigation("zone1", duration)
                if success:
                    st.success(message)
                    refresh_dashboard_data()
                else:
                    st.error(message)

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="dashboard-card"><div class="card-header">🚰 Zone 2 - Flower Beds</div>',
                    unsafe_allow_html=True)

        zone2_moisture = soil_moisture.get('zone2', 0)
        status_text, status_class, _ = get_moisture_status(zone2_moisture)

        st.markdown(f"""
            <div style="text-align: center; margin: 1rem 0;">
                <div style="font-size: 2rem; color: #2c3e50; margin-bottom: 0.5rem;">{zone2_moisture:.1f}%</div>
                <span class="status-badge {status_class}">{status_text}</span>
            </div>
        """, unsafe_allow_html=True)

        with st.form("zone2_irrigation"):
            duration = st.slider("Irrigation Duration (minutes)", 1, 30, 5, key="zone2_duration")
            if st.form_submit_button("💧 Start Irrigation", use_container_width=True):
                success, message = start_irrigation("zone2", duration)
                if success:
                    st.success(message)
                    refresh_dashboard_data()
                else:
                    st.error(message)

        st.markdown('</div>', unsafe_allow_html=True)

    # Irrigation Guidelines
    st.markdown("""
    <div class="dashboard-card">
        <div class="card-header">💡 Irrigation Guidelines</div>
        <ul style="color: #2c3e50;">
            <li><strong>Optimal Range:</strong> 60-80% moisture</li>
            <li><strong>Moderate Range:</strong> 40-60% moisture - monitor closely</li>
            <li><strong>Critical Range:</strong> Below 40% - irrigation recommended</li>
            <li><strong>Typical Duration:</strong> 5-10 minutes for light irrigation</li>
            <li><strong>Water Conservation:</strong> System optimizes usage based on weather data</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)


def render_analytics():
    """Render analytics page"""
    render_header()

    st.markdown('<h2 style="margin: 2rem 0 1rem 0; color: #2c3e50;">Analytics & Reports</h2>', unsafe_allow_html=True)

    # Get historical data
    with st.spinner("Loading analytics data..."):
        historical_data = get_historical_data(7)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="dashboard-card"><div class="card-header">💧 Water Usage Analytics</div>',
                    unsafe_allow_html=True)

        if historical_data:
            df = pd.DataFrame(historical_data)
            if 'date' in df.columns and 'avg_moisture' in df.columns:
                # Create water usage estimation based on moisture levels
                df['estimated_water_need'] = (60 - df['avg_moisture']).clip(lower=0)

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=df['date'],
                    y=df['estimated_water_need'],
                    marker_color='#3498db',
                    name='Estimated Water Need (L)'
                ))

                fig.update_layout(
                    height=300,
                    margin=dict(l=20, r=20, t=20, b=20),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    xaxis_title="Date",
                    yaxis_title="Liters (Estimated)"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Insufficient data for water usage analytics")
        else:
            st.info("No analytics data available yet")

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="dashboard-card"><div class="card-header">📈 Efficiency Metrics</div>',
                    unsafe_allow_html=True)

        # Get current data for metrics
        data = st.session_state.auth.get('data', {})
        system_metrics = data.get('system_metrics', {})

        metrics = [
            {"label": "Water Saved", "value": f"{system_metrics.get('energy_saved', 0):.0f}%", "trend": "↑"},
            {"label": "System Uptime", "value": f"{system_metrics.get('uptime', 0):.1f}%", "trend": "↑"},
            {"label": "Data Accuracy", "value": "98%", "trend": "→"},
            {"label": "API Reliability", "value": "99.5%", "trend": "↑"}
        ]

        for metric in metrics:
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0; border-bottom: 1px solid #f0f0f0;">
                    <span style="color: #2c3e50;">{metric['label']}</span>
                    <div>
                        <span style="font-weight: 600; color: #2c3e50;">{metric['value']}</span>
                        <span style="color: #27ae60; margin-left: 0.5rem;">{metric['trend']}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Data Quality Report
    st.markdown('<div class="dashboard-card"><div class="card-header">📊 Data Quality Report</div>',
                unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Data Points", "1,247", "12 today")
    with col2:
        st.metric("Data Sources", "2", "APIs")
    with col3:
        st.metric("Update Frequency", "1 hour", "Automatic")
    with col4:
        st.metric("Data Freshness", "98%", "Excellent")

    st.markdown('</div>', unsafe_allow_html=True)


def render_alerts():
    """Render alerts page"""
    render_header()

    st.markdown('<h2 style="margin: 2rem 0 1rem 0; color: #2c3e50;">System Alerts</h2>', unsafe_allow_html=True)

    # Get alerts from API
    with st.spinner("Loading alerts..."):
        alerts = get_alerts()

    if alerts:
        st.markdown(f"**Active Alerts:** {len(alerts)}")

        for alert in alerts:
            alert_id = alert.get('id')
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
                            Time: {alert.get('timestamp', '')}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            with col2:
                if not alert.get('acknowledged'):
                    if st.button("Acknowledge", key=f"ack_{alert_id}", use_container_width=True):
                        if acknowledge_alert(alert_id):
                            st.success("Alert acknowledged!")
                            st.rerun()
                        else:
                            st.error("Failed to acknowledge alert")
                else:
                    st.markdown("""
                        <div style="text-align: center; padding: 0.5rem; background: #e8f5e8; border-radius: 4px; color: #2e7d32;">
                            ✅ Acknowledged
                        </div>
                    """, unsafe_allow_html=True)

    else:
        st.markdown("""
            <div style="text-align: center; padding: 4rem 2rem; color: #7f8c8d;">
                <div style="font-size: 4rem; margin-bottom: 1rem;">✅</div>
                <h3 style="color: #2e7d32; margin-bottom: 0.5rem;">No Active Alerts</h3>
                <p>All systems are operating normally.</p>
            </div>
        """, unsafe_allow_html=True)


def render_settings():
    """Render settings page"""
    render_header()

    st.markdown('<h2 style="margin: 2rem 0 1rem 0; color: #2c3e50;">System Settings</h2>', unsafe_allow_html=True)

    # Get current settings
    settings = get_system_settings()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="dashboard-card"><div class="card-header">⚙️ Irrigation Settings</div>',
                    unsafe_allow_html=True)

        # Soil moisture threshold
        current_threshold = float(settings.get('soil_moisture_threshold', '40'))
        new_threshold = st.slider(
            "Soil Moisture Alert Threshold (%)",
            min_value=20,
            max_value=80,
            value=int(current_threshold),
            help="Alert when soil moisture drops below this level"
        )

        # Temperature threshold
        current_temp_threshold = float(settings.get('temperature_threshold', '35'))
        new_temp_threshold = st.slider(
            "Temperature Alert Threshold (°C)",
            min_value=25,
            max_value=45,
            value=int(current_temp_threshold),
            help="Alert when temperature exceeds this level"
        )

        if st.button("Save Settings", use_container_width=True):
            if update_system_setting('soil_moisture_threshold', str(new_threshold)):
                st.success("Soil moisture threshold updated!")
            if update_system_setting('temperature_threshold', str(new_temp_threshold)):
                st.success("Temperature threshold updated!")
            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="dashboard-card"><div class="card-header">👤 User Profile</div>',
                    unsafe_allow_html=True)

        user = st.session_state.auth.get('user', {})
        if user:
            st.markdown(f"""
                <div style="margin-bottom: 1.5rem;">
                    <div class="form-group">
                        <div class="form-label">Username</div>
                        <div style="padding: 0.75rem; background: #f8f9fa; border-radius: 4px; border: 1px solid #e9ecef;">
                            {user.get('username', 'N/A')}
                        </div>
                    </div>
                    <div class="form-group">
                        <div class="form-label">Email</div>
                        <div style="padding: 0.75rem; background: #f8f9fa; border-radius: 4px; border: 1px solid #e9ecef;">
                            {user.get('email', 'N/A')}
                        </div>
                    </div>
                    <div class="form-group">
                        <div class="form-label">Full Name</div>
                        <div style="padding: 0.75rem; background: #f8f9fa; border-radius: 4px; border: 1px solid #e9ecef;">
                            {user.get('full_name', 'N/A')}
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Weather Information Section
    st.markdown('<h3 style="margin: 2rem 0 1rem 0; color: #2c3e50;">Weather Conditions</h3>', unsafe_allow_html=True)

    # Get current data for weather section
    data = st.session_state.auth.get('data', {})
    weather_data = data.get('weather', {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        temp = weather_data.get('temperature', 0)
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">🌡️ Temperature</div>
                <div class="metric-value" style="color: #e74c3c;">{temp:.1f}°C</div>
                <div style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem;">
                    Current temperature
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col2:
        humidity = weather_data.get('humidity', 0)
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">💧 Humidity</div>
                <div class="metric-value" style="color: #3498db;">{humidity:.1f}%</div>
                <div style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem;">
                    Relative humidity
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col3:
        wind_speed = weather_data.get('wind_speed', 0)
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">💨 Wind Speed</div>
                <div class="metric-value" style="color: #9b59b6;">{wind_speed:.1f}</div>
                <div style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem;">
                    m/s - Affects evaporation
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col4:
        pressure = weather_data.get('pressure', 0)
        st.markdown(f"""
            <div class="dashboard-card">
                <div class="card-header">📊 Pressure</div>
                <div class="metric-value" style="color: #f39c12;">{pressure:.1f}</div>
                <div style="margin-top: 1rem; color: #7f8c8d; font-size: 0.9rem;">
                    kPa - Weather patterns
                </div>
            </div>
        """, unsafe_allow_html=True)

    # System Information
    st.markdown('<div class="dashboard-card"><div class="card-header">🔧 System Information</div>',
                unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        # Test API connection
        try:
            health_response = requests.get(f"{API_BASE_URL}/health", timeout=5)
            status = "Connected" if health_response.status_code == 200 else "⚠️ Issues"
        except:
            status = "Offline"

        st.metric("API Status", status)

    with col2:
        refresh_status = st.session_state.auth.get('data_refresh_status', {})
        last_success = refresh_status.get('last_success', 'Never')
        st.metric("Last Data Sync", "Recent" if last_success != 'Never' else "Never")

    with col3:
        st.metric("System Version", "v1.0.0", "Live")

    with col4:
        st.metric("Data Sources", "2", "APIs")

    # Debug information (collapsible)
    with st.expander("Debug Information"):
        st.json(st.session_state.auth.get('data_refresh_status', {}))

        if st.session_state.auth.get('api_errors'):
            st.write("Recent API Errors:")
            for error in st.session_state.auth['api_errors'][-5:]:
                st.write(f"- {error['timestamp']}: {error['type']} - {error['message']}")

    st.markdown('</div>', unsafe_allow_html=True)


def main():
    """Main application controller"""

    # Check authentication
    if not st.session_state.auth['authenticated']:
        render_auth_page()
        return

    # Render authenticated app
    render_sidebar()

    # Render current page
    current_page = st.session_state.auth['current_page']

    try:
        if current_page == 'dashboard':
            render_dashboard()
        elif current_page == 'sensors':
            render_sensor_data()
        elif current_page == 'irrigation':
            render_irrigation()
        elif current_page == 'analytics':
            render_analytics()
        elif current_page == 'alerts':
            render_alerts()
        elif current_page == 'settings':
            render_settings()
    except Exception as e:
        st.error(f"Error rendering page: {str(e)}")
        log_error("page_render", f"Failed to render {current_page}: {str(e)}")
        st.info("Please try refreshing the page or check the API connection.")


if __name__ == "__main__":
    main()