import os
from dotenv import load_dotenv

load_dotenv()


class FrontendConfig:
    # API Configuration
    
    API_BASE_URL = os.getenv("API_BASE_URL", "https://smart-crop-monitor-gdsg.onrender.com")
    API_TIMEOUT = int(os.getenv("API_TIMEOUT", "30"))

    # Application Settings
    APP_NAME = "IoT Smart Crop Monitoring System"
    APP_VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # Dashboard Settings
    AUTO_REFRESH_INTERVAL = 300  # 5 minutes
    MAX_DATA_POINTS = 1000

    # Visualization Settings
    CHART_HEIGHT = 400
    COLOR_SCHEME = {
        'primary': '#3498db',
        'success': '#27ae60',
        'warning': '#f39c12',
        'danger': '#e74c3c',
        'info': '#17a2b8'
    }


config = FrontendConfig()
