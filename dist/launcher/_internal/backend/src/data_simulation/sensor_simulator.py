import numpy as np
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Any
import random

logger = logging.getLogger(__name__)


class SensorSimulator:
    """Simulates IoT sensor data with realistic patterns"""
    #For fallback
    def __init__(self):
        self.zone_configs = {
            "zone1": {
                "crop_type": "vegetables",
                "soil_type": "loam",
                "optimal_moisture": (60, 80)
            },
            "zone2": {
                "crop_type": "flowers",
                "soil_type": "clay_loam",
                "optimal_moisture": (50, 70)
            }
        }

    def generate_sensor_data(self, zone: str, weather_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate realistic sensor data based on environmental conditions"""
        config = self.zone_configs.get(zone, self.zone_configs["zone1"])

        # Base values influenced by weather
        base_temp = weather_data.get('temperature', 22.0)
        base_humidity = weather_data.get('humidity', 65.0)
        solar_rad = weather_data.get('solar_radiation', 5.0)
        precipitation = weather_data.get('precipitation', 0.0)

        # Simulate soil moisture with realistic dynamics
        soil_moisture = self._simulate_soil_moisture(zone, precipitation, solar_rad, base_temp)

        # Generate sensor readings with realistic noise
        sensor_data = {
            "zone": zone,
            "sensor_type": "soil",
            "value": soil_moisture,
            "unit": "%",
            "timestamp": datetime.now().isoformat(),
            "source": "simulation"
        }

        return sensor_data

    def _simulate_soil_moisture(self, zone: str, precipitation: float, solar_radiation: float,
                                temperature: float) -> float:
        """Simulate realistic soil moisture dynamics"""
        # Base moisture level based on zone
        if zone == "zone1":
            base_moisture = 65.0  # Vegetables prefer more moisture
        else:
            base_moisture = 55.0  # Flowers can tolerate drier conditions

        # Adjust for precipitation
        moisture_change = precipitation * 15.0  # Precipitation increases moisture

        # Adjust for evaporation (increased by temperature and solar radiation)
        evaporation = (temperature - 20) * 0.5 + solar_radiation * 0.8
        moisture_change -= evaporation

        # Add some random variation
        random_variation = random.uniform(-2.0, 2.0)

        # Calculate final moisture (clamped to realistic range)
        final_moisture = base_moisture + moisture_change + random_variation

        # Ensure moisture stays within physical limits
        return max(10.0, min(95.0, final_moisture))

    def generate_temperature_reading(self, base_temp: float, zone: str) -> Dict[str, Any]:
        """Generate temperature sensor reading"""
        # Temperature varies slightly by zone and time of day
        hour = datetime.now().hour
        diurnal_variation = np.sin((hour - 14) * np.pi / 12) * 8  # Peak at 2 PM

        temp_variation = diurnal_variation + random.uniform(-1.5, 1.5)
        temperature = base_temp + temp_variation

        return {
            "zone": zone,
            "sensor_type": "temperature",
            "value": temperature,
            "unit": "°C",
            "timestamp": datetime.now().isoformat(),
            "source": "simulation"
        }

    def generate_light_reading(self, solar_radiation: float, zone: str) -> Dict[str, Any]:
        """Generate light level sensor reading"""
        # Convert solar radiation to light intensity (simplified)
        light_intensity = solar_radiation * 200 + random.uniform(-50, 50)

        return {
            "zone": zone,
            "sensor_type": "light",
            "value": max(0, light_intensity),
            "unit": "lux",
            "timestamp": datetime.now().isoformat(),
            "source": "simulation"
        }

    def generate_humidity_reading(self, base_humidity: float, zone: str) -> Dict[str, Any]:
        """Generate humidity sensor reading"""
        # Humidity varies based on temperature and time
        hour = datetime.now().hour
        # Higher humidity at night, lower during day
        diurnal_variation = np.sin((hour - 4) * np.pi / 12) * 15

        humidity = base_humidity + diurnal_variation + random.uniform(-5, 5)

        return {
            "zone": zone,
            "sensor_type": "humidity",
            "value": max(10, min(95, humidity)),
            "unit": "%",
            "timestamp": datetime.now().isoformat(),
            "source": "simulation"
        }