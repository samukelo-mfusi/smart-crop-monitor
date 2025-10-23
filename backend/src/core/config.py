import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    PROJECT_NAME = "IoT Smart Crop Monitoring"
    VERSION = "1.0.0"
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./iot_crop_monitoring.db")

    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 30
    RESET_TOKEN_EXPIRE_HOURS = 24

    FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8501")
    SECRET_KEY = "your_jwt_secret_key"
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "your_sendgrid_api_key")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@smartcrop.com")
    EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "False").lower() == "true"

    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "your_openweather_api_key")
    NASA_POWER_BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

    DEFAULT_LATITUDE = -29.8587           #durban coordinates
    DEFAULT_LONGITUDE = 31.0218

    DATA_COLLECTION_INTERVAL = 300
    DATA_RETENTION_DAYS = 90
    SIMULATION_INTERVAL = 60

    SOIL_MOISTURE_CRITICAL = 30.0
    SOIL_MOISTURE_WARNING = 40.0
    TEMPERATURE_CRITICAL = 35.0

    MQTT_ENABLED = os.getenv("MQTT_ENABLED", "True").lower() == "true"
    MQTT_BROKER = os.getenv("MQTT_BROKER", "broker.hivemq.com")
    MQTT_PORT = int(os.getenv("MQTT_PORT", "8883"))
    MQTT_USERNAME = os.getenv("MQTT_USERNAME", "your_mqtt_username")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "your_mqtt_password")

    HTTP_ENABLED = os.getenv("HTTP_ENABLED", "True").lower() == "true"
    HTTP_PORT = int(os.getenv("HTTP_PORT", "8081"))
    HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")

    COAP_ENABLED = os.getenv("COAP_ENABLED", "True").lower() == "true"
    COAP_PORT = int(os.getenv("COAP_PORT", "5683"))
    COAP_HOST = os.getenv("COAP_HOST", "0.0.0.0")

    MQTT_TOPIC_SENSOR_DATA = "crop_monitoring/sensors/data"
    MQTT_TOPIC_ALERTS = "crop_monitoring/alerts"
    MQTT_TOPIC_COMMANDS = "crop_monitoring/commands"
    MQTT_TOPIC_SYSTEM_STATUS = "crop_monitoring/system/status"


settings = Settings()
