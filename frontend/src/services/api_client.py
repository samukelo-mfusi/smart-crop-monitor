import requests
import time
from datetime import datetime
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class APIClient:
    """Client for communicating with the backend API"""

    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = requests.Session()
        self.token: Optional[str] = None

    def set_token(self, token: str):
        """Set authentication token"""
        self.token = token

    def clear_token(self):
        """Clear authentication token"""
        self.token = None

    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None,
                     retry_count: int = 0) -> Optional[requests.Response]:
        """Make API request with error handling and retry logic"""
        url = f"{self.base_url}{endpoint}"
        headers = {}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        try:
            if method == "GET":
                response = self.session.get(url, headers=headers, timeout=self.timeout)
            elif method == "POST":
                headers["Content-Type"] = "application/json"
                response = self.session.post(url, headers=headers, json=data, timeout=self.timeout)
            elif method == "PUT":
                headers["Content-Type"] = "application/json"
                response = self.session.put(url, headers=headers, json=data, timeout=self.timeout)
            else:
                logger.error(f"Unsupported HTTP method: {method}")
                return None

            return response

        except requests.exceptions.Timeout:
            if retry_count < 2:
                time.sleep(1)
                return self.make_request(method, endpoint, data, retry_count + 1)
            logger.error(f"Request timeout after {retry_count + 1} retries: {url}")
            return None

        except requests.exceptions.ConnectionError:
            logger.error(f"Cannot connect to API: {url}")
            return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {str(e)}")
            return None

    def login(self, username: str, password: str, remember_me: bool = True) -> tuple[bool, str, Optional[Dict]]:
        """Authenticate user and get token"""
        data = {
            "username": username,
            "password": password,
            "remember_me": remember_me
        }

        try:
            response = requests.post(
                f"{self.base_url}/auth/login",  # ✅ Corrected path
                json=data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )

            if response and response.status_code == 200:
                token_data = response.json()
                self.token = token_data['access_token']
                return True, "Login successful", token_data
            else:
                error_msg = "Invalid username or password"
                if response:
                    try:
                        error_data = response.json()
                        error_msg = error_data.get('detail', error_msg)
                    except:
                        error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg, None
        except Exception as e:
            return False, f"Login error: {str(e)}", None

    def register(self, user_data: Dict[str, str]) -> tuple[bool, str]:
        """Register a new user"""
        response = self.make_request("POST", "/auth/register", user_data)

        if response and response.status_code in [200, 201]:
            return True, "Registration successful"
        else:
            error_msg = "Registration failed"
            if response is not None:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', error_msg)
                except Exception:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
            return False, error_msg

    def get_dashboard_data(self) -> Optional[Dict]:
        response = self.make_request("GET", "/api/dashboard-data")
        if response and response.status_code == 200:
            return response.json()
        return None

    def get_sensor_data(self, hours: int = 24) -> list:
        response = self.make_request("GET", f"/api/data/readings?hours={hours}")
        if response and response.status_code == 200:
            return response.json()
        return []

    def get_historical_data(self, days: int = 7) -> list:
        response = self.make_request("GET", f"/api/historical-data?days={days}")
        if response and response.status_code == 200:
            return response.json().get('historical_data', [])
        return []

    def start_irrigation(self, zone: str, duration: int) -> tuple[bool, str]:
        data = {"zone": zone, "duration": duration}
        response = self.make_request("POST", "/api/control/irrigate", data)
        if response and response.status_code == 200:
            return True, "Irrigation started successfully"
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}" if response else "Failed to start irrigation"
            return False, error_msg

    def get_alerts(self, acknowledged: bool = False) -> list:
        response = self.make_request("GET", f"/api/data/alerts?acknowledged={str(acknowledged).lower()}")
        if response and response.status_code == 200:
            return response.json()
        return []

    def acknowledge_alert(self, alert_id: int) -> bool:
        response = self.make_request("POST", f"/api/alerts/{alert_id}/acknowledge")
        return response and response.status_code == 200

    def get_system_settings(self) -> Dict:
        response = self.make_request("GET", "/api/system/settings")
        if response and response.status_code == 200:
            return response.json().get('settings', {})
        return {}

    def update_system_setting(self, key: str, value: str) -> bool:
        data = {"setting_value": value}
        response = self.make_request("PUT", f"/api/system/settings/{key}", data)
        return response and response.status_code == 200

    def refresh_real_world_data(self) -> tuple[bool, str]:
        response = self.make_request("POST", "/api/data/refresh")
        if response and response.status_code == 200:
            return True, "Data refresh started"
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}" if response else "Failed to start data refresh"
            return False, error_msg

    def get_data_status(self) -> Optional[Dict]:
        response = self.make_request("GET", "/api/data/status")
        if response and response.status_code == 200:
            return response.json()
        return None

    def health_check(self) -> bool:
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
