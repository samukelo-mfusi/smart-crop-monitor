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
    SECRET_KEY = "LQdYp-ETb1fuXboycAgkHSaPazAHQJ_reZ3BYUmUOtlKMkpPk0xh2pkzfiuQRcvwnlhWAHzKoSkao4XgUek5RQ"
    SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "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")
    FROM_EMAIL = os.getenv("FROM_EMAIL", "noreply@smartcrop.com")
    EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "False").lower() == "true"

    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "8b90ff8c58c735fa2f234f3d62e59a1c")
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
    MQTT_USERNAME = os.getenv("MQTT_USERNAME", "hivemq.client.1761030905773")
    MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "0r8xAs?>@d.Iu13JEHLy")

    HTTP_ENABLED = os.getenv("HTTP_ENABLED", "True").lower() == "true"
<<<<<<< HEAD
    HTTP_PORT = int(os.getenv("HTTP_PORT", "8080"))
=======
    HTTP_PORT = int(os.getenv("HTTP_PORT", "8081"))
>>>>>>> b46545bf3 (Add build and dist folders)
    HTTP_HOST = os.getenv("HTTP_HOST", "0.0.0.0")

    COAP_ENABLED = os.getenv("COAP_ENABLED", "True").lower() == "true"
    COAP_PORT = int(os.getenv("COAP_PORT", "5683"))
    COAP_HOST = os.getenv("COAP_HOST", "0.0.0.0")

    MQTT_TOPIC_SENSOR_DATA = "crop_monitoring/sensors/data"
    MQTT_TOPIC_ALERTS = "crop_monitoring/alerts"
    MQTT_TOPIC_COMMANDS = "crop_monitoring/commands"
    MQTT_TOPIC_SYSTEM_STATUS = "crop_monitoring/system/status"


settings = Settings()