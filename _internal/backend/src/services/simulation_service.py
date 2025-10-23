import asyncio
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from ..data_simulation.sensor_simulator import SensorSimulator
from ..data_simulation.nasa_power_client import NASAPowerClient
from ..data_simulation.openweather_client import OpenWeatherClient
from ..core.config import settings

logger = logging.getLogger(__name__)


class SimulationService:
    """Service for managing sensor simulation"""

    def __init__(self):
        self.sensor_simulator = SensorSimulator()
        self.nasa_client = NASAPowerClient()
        self.weather_client = OpenWeatherClient(settings.OPENWEATHER_API_KEY)
        self.is_running = False

    async def start_simulation_cycle(self):
        """Start the simulation cycle"""
        self.is_running = True
        logger.info("Sensor simulation service started")

        while self.is_running:
            try:
                # Simulate periodic data generation
                await asyncio.sleep(settings.SIMULATION_INTERVAL)
                logger.debug("Simulation cycle completed")

            except Exception as e:
                logger.error(f"Error in simulation cycle: {e}")
                await asyncio.sleep(60)

    def generate_sample_data(self) -> dict:
        """Generate sample sensor data for testing"""
        # Get real environmental data
        nasa_data = self.nasa_client.get_agricultural_data(
            settings.DEFAULT_LATITUDE,
            settings.DEFAULT_LONGITUDE,
            datetime.now().strftime("%Y%m%d"),
            datetime.now().strftime("%Y%m%d")
        )

        weather_data = self.weather_client.get_current_weather(
            settings.DEFAULT_LATITUDE,
            settings.DEFAULT_LONGITUDE
        )

        # Generate sensor readings
        sensor_data = {}

        for zone in ['zone1', 'zone2']:
            sensor_data[zone] = {
                'soil': self.sensor_simulator.generate_sensor_data(zone, nasa_data),
                'temperature': self.sensor_simulator.generate_temperature_reading(
                    weather_data['temperature'], zone
                ),
                'humidity': self.sensor_simulator.generate_humidity_reading(
                    weather_data['humidity'], zone
                ),
                'light': self.sensor_simulator.generate_light_reading(
                    nasa_data.get('solar_radiation', 5.0), zone
                )
            }

        return sensor_data

    def stop_simulation(self):
        """Stop the simulation service"""
        self.is_running = False
        logger.info("Sensor simulation service stopped")