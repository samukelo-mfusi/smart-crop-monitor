import requests
import logging
from typing import Dict, Any
from datetime import datetime
import time

logger = logging.getLogger(__name__)


class OpenWeatherClient:
    """Production client for OpenWeatherMap API - REAL DATA ONLY"""

    BASE_URL = "http://api.openweathermap.org/data/2.5"

    def __init__(self, api_key: str):
        if not api_key or api_key == "Invalid API Key":
            raise ValueError("Valid OpenWeather API key required")

        self.api_key = api_key
        self.session = requests.Session()
        self.timeout = 30
        self.max_retries = 3

    def get_current_weather(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get current weather data"""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.BASE_URL}/weather"
                params = {
                    "lat": latitude,
                    "lon": longitude,
                    "appid": self.api_key,
                    "units": "metric"
                }

                logger.info(f"OpenWeather API Request: {latitude}, {longitude}")

                response = self.session.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    processed_data = self._process_weather_data(data)
                    logger.info("OpenWeather API: Successfully retrieved real weather data")
                    return processed_data

                elif response.status_code == 401:
                    logger.error("OpenWeather API: Invalid API key")
                    return self._get_error_state("Invalid API key")

                elif response.status_code == 429:
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"OpenWeather API: Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue

                else:
                    logger.error(f"OpenWeather API: HTTP {response.status_code}")
                    if attempt < self.max_retries - 1:
                        time.sleep(10 * (attempt + 1))
                        continue

            except requests.exceptions.Timeout:
                logger.warning(f"OpenWeather API: Timeout on attempt {attempt + 1}")
                if attempt < self.max_retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue

            except requests.exceptions.RequestException as e:
                logger.error(f"OpenWeather API: Request failed on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue

        logger.error("OpenWeather API: All retries failed")
        return self._get_error_state("API request failed")

    def _process_weather_data(self, data: Dict) -> Dict[str, Any]:
        """Process weather data into agricultural format"""
        try:
            main = data.get('main', {})
            weather = data.get('weather', [{}])[0]
            wind = data.get('wind', {})
            clouds = data.get('clouds', {})
            sys = data.get('sys', {})

            # Extract real weather data
            temperature = main.get('temp')
            humidity = main.get('humidity')
            pressure = main.get('pressure')
            wind_speed = wind.get('speed')
            wind_direction = wind.get('deg')
            cloud_coverage = clouds.get('all')
            visibility = data.get('visibility')

            # Calculate agricultural metrics
            solar_radiation = self._estimate_solar_radiation(cloud_coverage)
            evapotranspiration = self._calculate_et0(temperature, humidity, wind_speed, solar_radiation)

            # Data validation
            if not all(val is not None for val in [temperature, humidity, pressure]):
                logger.warning("OpenWeather API: Incomplete data received")
                return self._get_error_state("Incomplete data")

            return {
                "temperature": temperature,
                "humidity": humidity,
                "pressure": pressure,
                "description": weather.get('description', ''),
                "icon": weather.get('icon', ''),
                "wind_speed": wind_speed,
                "wind_direction": wind_direction,
                "visibility": visibility,
                "cloud_coverage": cloud_coverage,
                "solar_radiation": solar_radiation,
                "evapotranspiration": evapotranspiration,
                "sunrise": sys.get('sunrise'),
                "sunset": sys.get('sunset'),
                "data_source": "openweather",
                "timestamp": datetime.now().isoformat(),
                "data_quality": "high",
                "coordinates": {
                    "latitude": data.get('coord', {}).get('lat'),
                    "longitude": data.get('coord', {}).get('lon')
                }
            }

        except Exception as e:
            logger.error(f"OpenWeather API: Error processing data: {e}")
            return self._get_error_state("Data processing error")

    def _estimate_solar_radiation(self, cloud_coverage: float) -> float:
        """Estimate solar radiation based on cloud coverage"""
        # Clear sky radiation ~ 1000 W/m², reduced by clouds
        clear_sky_radiation = 1000.0
        if cloud_coverage is None:
            return clear_sky_radiation

        cloud_reduction = cloud_coverage / 100.0
        return clear_sky_radiation * (1 - cloud_reduction * 0.7)

    def _calculate_et0(self, temp: float, humidity: float, wind_speed: float, solar_radiation: float) -> float:
        """Calculate reference evapotranspiration"""
        if any(val is None for val in [temp, humidity, wind_speed, solar_radiation]):
            return 0.0

        # Simplified FAO Penman-Monteith
        temp_factor = max(0, temp) / 25.0
        humidity_factor = (100 - humidity) / 100.0
        wind_factor = 1 + (wind_speed / 10.0)
        radiation_factor = solar_radiation / 1000.0

        et0 = temp_factor * humidity_factor * wind_factor * radiation_factor * 4.0
        return max(0.1, min(10.0, et0))

    def get_forecast(self, latitude: float, longitude: float) -> Dict[str, Any]:
        """Get REAL weather forecast - PRODUCTION VERSION"""
        for attempt in range(self.max_retries):
            try:
                url = f"{self.BASE_URL}/forecast"
                params = {
                    "lat": latitude,
                    "lon": longitude,
                    "appid": self.api_key,
                    "units": "metric",
                    "cnt": 8  # Next 24 hours
                }

                response = self.session.get(url, params=params, timeout=self.timeout)

                if response.status_code == 200:
                    data = response.json()
                    return self._process_forecast_data(data)

                elif response.status_code == 429:
                    wait_time = (attempt + 1) * 30
                    logger.warning(f"OpenWeather Forecast: Rate limited, waiting {wait_time}s")
                    time.sleep(wait_time)
                    continue

            except requests.exceptions.RequestException as e:
                logger.error(f"OpenWeather Forecast: Request failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(10 * (attempt + 1))
                    continue

        logger.error("OpenWeather Forecast: All retries failed")
        return self._get_error_state("Forecast unavailable")

    def _process_forecast_data(self, data: Dict) -> Dict[str, Any]:
        """Process forecast data for irrigation planning"""
        try:
            forecasts = data.get('list', [])

            if not forecasts:
                return self._get_error_state("No forecast data")

            # Analyze next 24 hours for irrigation decisions
            rain_forecasts = []
            temps = []

            for forecast in forecasts[:8]:  # Next 24 hours
                main = forecast.get('main', {})
                weather = forecast.get('weather', [{}])[0]
                rain = forecast.get('rain', {})

                temps.append(main.get('temp'))
                rain_forecasts.append(rain.get('3h', 0) > 0 or 'rain' in weather.get('description', '').lower())

            rain_expected = any(rain_forecasts)
            max_temp = max(temps) if temps else None
            min_temp = min(temps) if temps else None

            return {
                "rain_expected": rain_expected,
                "max_temperature": max_temp,
                "min_temperature": min_temp,
                "forecast_hours": len(forecasts),
                "data_source": "openweather_forecast",
                "timestamp": datetime.now().isoformat(),
                "data_quality": "high"
            }

        except Exception as e:
            logger.error(f"OpenWeather Forecast: Error processing data: {e}")
            return self._get_error_state("Forecast processing error")

    def _get_error_state(self, error_message: str = "API error") -> Dict[str, Any]:
        """Return error state instead of demo data"""
        return {
            "temperature": None,
            "humidity": None,
            "pressure": None,
            "wind_speed": None,
            "data_source": "error",
            "timestamp": datetime.now().isoformat(),
            "data_quality": "error",
            "error": error_message
        }