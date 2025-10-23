import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
from typing import Dict, Any
import time

logger = logging.getLogger(__name__)


class NASAPowerClient:
    """Client for NASA POWER API"""

    BASE_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"

    def __init__(self):
        self.session = requests.Session()
        # Production timeout settings
        self.timeout = 45
        self.max_retries = 3

    def get_agricultural_data(self, latitude: float, longitude: float, start_date: str, end_date: str) -> Dict[
        str, Any]:
        """Agricultural data from NASA POWER API - ENHANCED DEBUGGING"""
        for attempt in range(self.max_retries):
            try:
                # Agricultural parameters for crop monitoring
                parameters = [
                    "T2M",  # Temperature at 2 meters (°C)
                    "RH2M",  # Relative humidity at 2 meters (%)
                    "PRECTOTCORR",  # Precipitation (mm/day)
                    "ALLSKY_SFC_SW_DWN",  # Solar radiation (W/m²)
                    "WS2M",  # Wind speed at 2 meters (m/s)
                    "GWETTOP"  # Surface soil wetness (fraction)
                ]

                params = {
                    "parameters": ",".join(parameters),
                    "community": "AG",
                    "longitude": longitude,
                    "latitude": latitude,
                    "start": start_date,
                    "end": end_date,
                    "format": "JSON"
                }

                logger.info(
                    f"NASA POWER API Request: lat={latitude}, lon={longitude}, dates={start_date} to {end_date}")

                response = self.session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self.timeout,
                    verify=False
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"NASA API Response keys: {list(data.keys())}")

                    # Check response structure
                    if 'properties' in data:
                        properties = data['properties']
                        logger.debug(f"NASA Properties keys: {list(properties.keys())}")

                        if 'parameter' in properties:
                            parameters_data = properties['parameter']
                            logger.debug(f"NASA Parameter keys: {list(parameters_data.keys())}")

                            # Check if we have any data in the parameters
                            for param_name, param_data in parameters_data.items():
                                if param_data and isinstance(param_data, dict):
                                    valid_dates = [date for date, value in param_data.items() if
                                                   self._is_valid_data(value)]
                                    if valid_dates:
                                        logger.info(
                                            f"NASA Parameter '{param_name}' has {len(valid_dates)} valid data points")
                                        logger.debug(f"Sample data for {param_name}: {list(param_data.items())[:3]}")

                            processed_data = self._process_nasa_data(data)
                            if processed_data and processed_data.get('data_quality') != 'error':
                                logger.info("NASA POWER API: Successfully retrieved real agricultural data")
                                return processed_data
                        else:
                            logger.warning("NASA POWER API: No 'parameter' key in properties")
                    else:
                        logger.warning(f"NASA POWER API: No 'properties' key in response. Response: {data}")

                else:
                    logger.error(f"NASA POWER API: HTTP {response.status_code} - {response.text}")

            except requests.exceptions.Timeout:
                logger.warning(f"NASA POWER API: Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue

            except requests.exceptions.RequestException as e:
                logger.error(f"NASA POWER API: Request failed on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue

        logger.error("NASA POWER API: All retries failed - returning error state")
        return self._get_error_state()

    def _process_nasa_data(self, data: Dict) -> Dict[str, Any]:
        """Process NASA POWER data into usable format - IMPROVED HANDLING"""
        try:
            properties = data.get('properties', {})
            parameters = properties.get('parameter', {})

            if not parameters:
                logger.error("NASA POWER API: No parameters in response")
                return self._get_error_state()

            # Log available parameters for debugging
            available_params = list(parameters.keys())
            logger.info(f"NASA Available parameters: {available_params}")

            # Try to find any valid data point across all parameters
            latest_date = None
            valid_data_found = False

            for param_name, param_data in parameters.items():
                if param_data and isinstance(param_data, dict):
                    valid_dates = [date for date, value in param_data.items() if self._is_valid_data(value)]
                    if valid_dates:
                        if not latest_date or max(valid_dates) > latest_date:
                            latest_date = max(valid_dates)
                        valid_data_found = True
                        logger.info(f"Found valid data for {param_name} on {latest_date}")

            if not valid_data_found or not latest_date:
                logger.error("NASA POWER API: No valid data found in any parameter")
                return self._get_error_state()

            # Extract data for the latest valid date
            temperature = parameters.get('T2M', {}).get(latest_date)
            humidity = parameters.get('RH2M', {}).get(latest_date)
            precipitation = parameters.get('PRECTOTCORR', {}).get(latest_date, 0.0)
            solar_radiation = parameters.get('ALLSKY_SFC_SW_DWN', {}).get(latest_date)
            wind_speed = parameters.get('WS2M', {}).get(latest_date)

            # REAL SOIL MOISTURE from NASA (GWETTOP: surface soil wetness 0-1)
            soil_wetness = parameters.get('GWETTOP', {}).get(latest_date)
            soil_moisture_percent = soil_wetness * 100 if soil_wetness is not None else None

            # Validate we have at least some core data
            if any(val is not None for val in [temperature, soil_moisture_percent, humidity]):
                return {
                    "temperature": temperature,
                    "humidity": humidity,
                    "precipitation": precipitation,
                    "solar_radiation": solar_radiation,
                    "wind_speed": wind_speed,
                    "soil_moisture": soil_moisture_percent,
                    "data_source": "nasa_power",
                    "timestamp": latest_date,
                    "data_quality": "high",
                    "parameters_available": available_params
                }
            else:
                logger.warning("NASA POWER API: Insufficient valid data")
                return self._get_error_state()

        except Exception as e:
            logger.error(f"NASA POWER API: Error processing data: {e}")
            return self._get_error_state()

    def _get_latest_date(self, properties: Dict) -> str:
        """Get the latest date with valid data"""
        try:
            # Find the most recent date with temperature data
            temp_data = properties.get('T2M', {})
            if temp_data:
                valid_dates = [date for date, value in temp_data.items()
                               if self._is_valid_data(value)]
                if valid_dates:
                    return max(valid_dates)
            return None
        except Exception as e:
            logger.error(f"Error finding latest date: {e}")
            return None

    def _is_valid_data(self, value: float) -> bool:
        """Validate NASA data values"""
        if value is None:
            return False
        if value == -999.0:  # NASA missing data indicator
            return False
        if abs(value) > 10000:  # Unrealistic values
            return False
        return True

    def _get_error_state(self) -> Dict[str, Any]:
        """Return error state instead of demo data"""
        return {
            "temperature": None,
            "humidity": None,
            "precipitation": None,
            "solar_radiation": None,
            "wind_speed": None,
            "soil_moisture": None,
            "data_source": "error",
            "timestamp": datetime.now().strftime("%Y%m%d"),
            "data_quality": "error",
            "error": "Failed to retrieve NASA POWER data"
        }