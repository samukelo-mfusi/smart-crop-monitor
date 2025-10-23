import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
import time

from ..data_simulation.nasa_power_client import NASAPowerClient
from ..data_simulation.openweather_client import OpenWeatherClient
from ..core.config import settings

logger = logging.getLogger(__name__)


class HistoricalDataService:
    """Service to generate historical data using real NASA POWER API data"""

    def __init__(self):
        self.nasa_client = NASAPowerClient()
        self.weather_client = OpenWeatherClient(settings.OPENWEATHER_API_KEY)

    def get_historical_data(self, days: int = 7) -> List[Dict[str, Any]]:
        """Get historical data using NASA POWER API for past dates"""
        historical_data = []

        for i in range(days):
            target_date = datetime.now() - timedelta(days=i)
            date_str = target_date.strftime('%Y-%m-%d')

            logger.info(f"Fetching historical data for {date_str}")

            # Get NASA data for this specific date
            nasa_data = self._get_nasa_data_for_date(target_date)

            # If NASA data is valid, use it directly
            if nasa_data and nasa_data.get('data_quality') != 'error':
                historical_data.append(self._format_historical_entry(target_date, nasa_data))
            else:
                # Fallback: Use current NASA data with date-based adjustments
                fallback_data = self._get_fallback_data_for_date(target_date)
                historical_data.append(fallback_data)

            # Small delay to be respectful to the API
            time.sleep(1)

        return list(reversed(historical_data))

    def _get_nasa_data_for_date(self, target_date: datetime) -> Dict[str, Any]:
        """Get NASA POWER data for a specific past date"""
        try:
            # NASA POWER API works with date ranges
            # For historical data, we request data for the specific target date
            start_date = target_date.strftime("%Y%m%d")
            end_date = target_date.strftime("%Y%m%d")

            logger.debug(f"Requesting NASA data for date: {start_date}")

            nasa_data = self.nasa_client.get_agricultural_data(
                settings.DEFAULT_LATITUDE,
                settings.DEFAULT_LONGITUDE,
                start_date,
                end_date
            )

            # Check if we got valid data
            if (nasa_data and
                    nasa_data.get('data_quality') != 'error' and
                    nasa_data.get('soil_moisture') is not None):

                logger.info(f"Successfully retrieved NASA data for {start_date}")
                return nasa_data
            else:
                logger.warning(f"No valid NASA data for {start_date}")
                return None

        except Exception as e:
            logger.error(f"Error getting NASA data for {target_date}: {e}")
            return None

    def _get_fallback_data_for_date(self, target_date: datetime) -> Dict[str, Any]:
        """Generate fallback data when NASA API fails for a specific date"""
        try:
            # Get current NASA data as baseline
            current_nasa_data = self._get_current_nasa_data()

            if current_nasa_data and current_nasa_data.get('data_quality') != 'error':
                # Adjust current data based on the target date
                return self._adjust_data_for_date(current_nasa_data, target_date)
            else:
                # Final fallback: seasonal simulation
                return self._get_seasonal_simulation(target_date)

        except Exception as e:
            logger.error(f"Error in fallback data for {target_date}: {e}")
            return self._get_seasonal_simulation(target_date)

    def _get_current_nasa_data(self) -> Dict[str, Any]:
        """Get current NASA data as baseline"""
        try:
            today = datetime.now()
            start_date = (today - timedelta(days=1)).strftime("%Y%m%d")
            end_date = today.strftime("%Y%m%d")

            return self.nasa_client.get_agricultural_data(
                settings.DEFAULT_LATITUDE,
                settings.DEFAULT_LONGITUDE,
                start_date,
                end_date
            )
        except Exception as e:
            logger.error(f"Error getting current NASA data: {e}")
            return None

    def _adjust_data_for_date(self, current_data: Dict[str, Any], target_date: datetime) -> Dict[str, Any]:
        """Adjust current NASA data to be realistic for the target date"""
        try:
            # Calculate days difference
            days_diff = (datetime.now() - target_date).days
            month = target_date.month

            seasonal_adjustments = self._get_seasonal_adjustments(month)

            # Apply seasonal adjustments
            adjusted_temperature = current_data.get('temperature', 24.0) + seasonal_adjustments['temp']
            adjusted_humidity = max(40, min(85, current_data.get('humidity', 65.0) + seasonal_adjustments['humidity']))

            # Soil moisture adjustment based on seasonal patterns
            base_moisture = current_data.get('soil_moisture', 65.0)
            adjusted_moisture = self._calculate_seasonal_moisture(base_moisture, month, days_diff)

            return self._format_historical_entry(target_date, {
                'temperature': adjusted_temperature,
                'humidity': adjusted_humidity,
                'soil_moisture': adjusted_moisture,
                'precipitation': current_data.get('precipitation', 0.0),
                'solar_radiation': current_data.get('solar_radiation', 5.0),
                'data_source': 'nasa_adjusted',
                'data_quality': 'adjusted'
            })

        except Exception as e:
            logger.error(f"Error adjusting data for date: {e}")
            return self._get_seasonal_simulation(target_date)

    def _get_seasonal_adjustments(self, month: int) -> Dict[str, float]:
        """Get seasonal adjustments for Durban, South Africa"""
        # Southern Hemisphere seasons
        if month in [12, 1, 2]:  # Summer
            return {'temp': 3.0, 'humidity': 8.0}
        elif month in [3, 4, 5]:  # Autumn
            return {'temp': 0.0, 'humidity': 2.0}
        elif month in [6, 7, 8]:  # Winter
            return {'temp': -4.0, 'humidity': -6.0}
        else:  # September, October, November - Spring
            return {'temp': 1.0, 'humidity': 4.0}

    def _calculate_seasonal_moisture(self, base_moisture: float, month: int, days_diff: int) -> float:
        """Calculate realistic soil moisture based on season"""
        # Seasonal moisture patterns
        if month in [12, 1, 2]:  # Summer - drier
            seasonal_adjustment = -8.0
        elif month in [6, 7, 8]:  # Winter - wetter
            seasonal_adjustment = 5.0
        else:  # Spring/Autumn
            seasonal_adjustment = 0.0

        # Add some daily variation
        daily_variation = (days_diff % 7) - 3  # Weekly pattern

        adjusted_moisture = base_moisture + seasonal_adjustment + daily_variation

        return max(25.0, min(85.0, adjusted_moisture))

    def _get_seasonal_simulation(self, target_date: datetime) -> Dict[str, Any]:
        """Generate completely simulated data based on seasonal patterns"""
        month = target_date.month
        day_of_week = target_date.weekday()

        # Base values by season
        if month in [12, 1, 2]:  # Summer
            base_temp = 26.0
            base_humidity = 68.0
            base_moisture = 58.0
        elif month in [6, 7, 8]:  # Winter
            base_temp = 18.0
            base_humidity = 58.0
            base_moisture = 72.0
        else:  # Spring/Autumn
            base_temp = 22.0
            base_humidity = 65.0
            base_moisture = 65.0

        # Weekend effect (less irrigation)
        if day_of_week >= 5:  # Weekend
            base_moisture -= 4

        # Random daily variation
        temp_variation = (day_of_week % 3) - 1
        moisture_variation = (day_of_week % 5) - 2

        return self._format_historical_entry(target_date, {
            'temperature': base_temp + temp_variation,
            'humidity': base_humidity,
            'soil_moisture': base_moisture + moisture_variation,
            'precipitation': 0.0,
            'solar_radiation': 5.0,
            'data_source': 'seasonal_simulation',
            'data_quality': 'simulated'
        })

    def _format_historical_entry(self, date: datetime, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format a historical data entry"""
        soil_moisture = data.get('soil_moisture', 65.0)

        return {
            'date': date.strftime('%Y-%m-%d'),
            'avg_moisture': round(soil_moisture, 1),
            'avg_temperature': round(data.get('temperature', 24.0), 1),
            'avg_humidity': round(data.get('humidity', 65.0), 1),
            'water_need': round(max(0, 70 - soil_moisture), 1),
            'data_source': data.get('data_source', 'unknown'),
            'data_quality': data.get('data_quality', 'unknown'),
            'solar_radiation': data.get('solar_radiation', 0),
            'precipitation': data.get('precipitation', 0)
        }