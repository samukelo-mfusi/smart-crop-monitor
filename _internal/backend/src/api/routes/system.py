from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any
from pydantic import BaseModel

from ...database.database import get_db
from ...database.crud import get_system_setting, create_or_update_setting, get_all_settings
from ...database.models import User
from ...api.dependencies import get_current_active_user
from ...services.data_services import DataService
from ...data_simulation.nasa_power_client import NASAPowerClient
from ...data_simulation.openweather_client import OpenWeatherClient

router = APIRouter()


class SettingUpdate(BaseModel):
    setting_value: str


@router.get("/system/settings")
def get_system_settings(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    settings = get_all_settings(db)
    settings_dict = {setting.key: setting.value for setting in settings}

    # Ensure default settings exist
    default_settings = {
        "soil_moisture_threshold": "40",
        "temperature_threshold": "35",
        "irrigation_duration": "10",
        "data_refresh_interval": "300"
    }

    for key, value in default_settings.items():
        if key not in settings_dict:
            create_or_update_setting(db, key, value)
            settings_dict[key] = value

    return {"settings": settings_dict}


@router.put("/system/settings/{setting_key}")
def update_system_setting(
        setting_key: str,
        setting_update: SettingUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    valid_settings = ["soil_moisture_threshold", "temperature_threshold",
                      "irrigation_duration", "data_refresh_interval"]

    if setting_key not in valid_settings:
        raise HTTPException(status_code=400, detail="Invalid setting key")

    setting = create_or_update_setting(db, setting_key, setting_update.setting_value)

    return {
        "success": True,
        "message": f"Setting {setting_key} updated",
        "new_value": setting.value
    }


@router.get("/system/status")
def get_system_status():
    return {
        "system": "operational",
        "version": "1.0.0",
        "data_sources": {
            "nasa_power": "active",
            "openweather": "active",
            "sensor_simulation": "active"
        },
        "last_data_refresh": datetime.now().isoformat(),
        "uptime": "100%"
    }

@router.get("/debug/api-status")
def debug_api_status(db: Session = Depends(get_db)):
    """Debug endpoint to check API status"""

    data_service = DataService()

    # Test NASA API directly
    nasa_client = NASAPowerClient()
    nasa_test = nasa_client.get_agricultural_data(
        -29.8587, 31.0218,
        (datetime.now() - timedelta(days=1)).strftime("%Y%m%d"),
        datetime.now().strftime("%Y%m%d")
    )

    # Test OpenWeather API directly
    weather_client = OpenWeatherClient("8b90ff8c58c735fa2f234f3d62e59a1c")
    weather_test = weather_client.get_current_weather(-29.8587, 31.0218)

    return {
        "nasa_api": nasa_test.get('data_quality', 'unknown'),
        "openweather_api": weather_test.get('data_quality', 'unknown'),
        "system_metrics": data_service.get_service_metrics()
    }