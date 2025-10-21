import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from streamlit import json
import math

from ..data_simulation.nasa_power_client import NASAPowerClient
from ..data_simulation.openweather_client import OpenWeatherClient
from ..data_simulation.sensor_simulator import SensorSimulator
from ..data_simulation.soil_moisture_model import SoilMoistureModel
from ..database.crud import create_sensor_reading, get_latest_sensor_readings, get_alerts, create_alert, get_all_users, \
    get_recent_irrigation_events
from ..processing.data_processor import DataProcessor
from ..alerts.alert_manager import AlertManager
from ..communication import protocol_manager
from ..core.config import settings
from ..database.database import SessionLocal

logger = logging.getLogger(__name__)


class LightLevelCalculator:
    """Light level calculation based on weather, time, and location"""

    @staticmethod
    def calculate_solar_radiation_to_lux(solar_radiation_wm2: float) -> float:
        """
        Convert solar radiation (W/m²) to illuminance (lux)
        Approximate conversion factor for daylight: 126.7 lux per W/m²
        """
        if solar_radiation_wm2 <= 0:
            return 0.0

        # More precise conversion considering solar spectrum
        conversion_factor = 126.7
        lux = solar_radiation_wm2 * conversion_factor

        # Bounds
        return max(0.0, min(120000.0, lux))

    @staticmethod
    def calculate_time_of_day_factor(current_hour: int, current_minute: int = 0) -> float:
        """
        Calculate light intensity based on time of day using solar position approximation
        Returns factor between 0.0 (night) and 1.0 (solar noon)
        """
        # Convert to decimal hours for smoother calculation
        decimal_hour = current_hour + current_minute / 60.0

        # Solar noon is approximately 12:00
        solar_noon = 12.0

        # Calculate hours from solar noon
        hours_from_noon = abs(decimal_hour - solar_noon)

        # Day length approximation (simplified)
        day_start = 6.0  # 6 AM
        day_end = 18.0  # 6 PM

        if decimal_hour < day_start or decimal_hour > day_end:
            # Night_time - minimal light
            return 0.01

        # Calculate position in day (0 = sunrise, 1 = sunset)
        day_position = (decimal_hour - day_start) / (day_end - day_start)

        # Use sine function for smooth daylight curve
        # Convert day position to radians for sine calculation
        radians = day_position * math.pi
        time_factor = math.sin(radians)

        # Ensure factor is never negative
        return max(0.1, time_factor)

    @staticmethod
    def calculate_cloud_cover_factor(cloud_cover_percent: float) -> float:
        """
        Calculate light reduction due to cloud cover
        """
        if cloud_cover_percent <= 0:
            return 1.0  # Clear sky

        if cloud_cover_percent >= 100:
            return 0.2  # Heavy overcast

        # Exponential reduction for more realistic cloud effects
        base_reduction = cloud_cover_percent / 100.0
        # More aggressive reduction for higher cloud cover
        cloud_factor = 1.0 - (base_reduction * 0.8)

        return max(0.2, cloud_factor)

    @staticmethod
    def calculate_weather_condition_factor(weather_description: str) -> float:
        """
        Calculate light reduction based on specific weather conditions
        """
        description = weather_description.lower()

        # Clear conditions
        if any(term in description for term in ['clear', 'sunny', 'fair']):
            return 1.0

        # Partly cloudy
        elif any(term in description for term in ['partly', 'scattered', 'few']):
            return 0.7

        # Cloudy
        elif any(term in description for term in ['cloudy', 'overcast', 'broken']):
            return 0.4

        # Light precipitation
        elif any(term in description for term in ['drizzle', 'light rain', 'mist', 'fog']):
            return 0.3

        # Rain
        elif any(term in description for term in ['rain', 'shower', 'precipitation']):
            return 0.2

        # Heavy rain/storms
        elif any(term in description for term in ['storm', 'thunder', 'heavy rain', 'downpour']):
            return 0.1

        # Snow
        elif any(term in description for term in ['snow', 'sleet', 'hail']):
            return 0.4  # Snow reflects light

        # Default for unknown conditions
        else:
            return 0.5

    @staticmethod
    def calculate_seasonal_factor(current_month: int, latitude: float) -> float:
        """
        Calculate seasonal light variation based on month and latitude
        Simplified model for demonstration
        """
        # Northern hemisphere seasonal adjustment
        if latitude >= 0:
            # Summer months (June-August)
            if 5 <= current_month <= 7:
                return 1.2
            # Winter months (December-February)
            elif current_month == 12 or current_month <= 2:
                return 0.6
            # Spring/Fall
            else:
                return 0.9
        else:
            # Southern hemisphere (inverse)
            if 5 <= current_month <= 7:
                return 0.6
            elif current_month == 12 or current_month <= 2:
                return 1.2
            else:
                return 0.9

    @staticmethod
    def calculate_comprehensive_light_level(
            cloud_cover: float,
            weather_description: str,
            current_hour: int,
            current_minute: int = 0,
            solar_radiation: Optional[float] = None,
            latitude: float = 40.0,  # Default to NYC latitude
            current_month: Optional[int] = None
    ) -> float:
        """
        Calculate comprehensive light level using multiple factors
        """
        try:
            # Use current month if not provided
            if current_month is None:
                current_month = datetime.now().month

            # If we have direct solar radiation data, use it as base
            if solar_radiation is not None and solar_radiation > 0:
                base_light = LightLevelCalculator.calculate_solar_radiation_to_lux(solar_radiation)
            else:
                # Base light level for clear day at noon (in lux)
                base_light = 100000.0

            # Apply all adjustment factors
            time_factor = LightLevelCalculator.calculate_time_of_day_factor(current_hour, current_minute)
            cloud_factor = LightLevelCalculator.calculate_cloud_cover_factor(cloud_cover)
            weather_factor = LightLevelCalculator.calculate_weather_condition_factor(weather_description)
            seasonal_factor = LightLevelCalculator.calculate_seasonal_factor(current_month, latitude)

            # Calculate final light level
            light_level = base_light * time_factor * cloud_factor * weather_factor * seasonal_factor

            # Ensure realistic bounds
            light_level = max(10.0, min(120000.0, light_level))

            logger.info(
                f"Comprehensive light calculation: "
                f"base={base_light:.0f} lux, "
                f"time_factor={time_factor:.2f}, "
                f"cloud_factor={cloud_factor:.2f}, "
                f"weather_factor={weather_factor:.2f}, "
                f"seasonal_factor={seasonal_factor:.2f}, "
                f"final={light_level:.0f} lux"
            )

            return light_level

        except Exception as e:
            logger.error(f"Error in comprehensive light calculation: {e}")
            # Fallback calculation
            return LightLevelCalculator.calculate_fallback_light_level(
                cloud_cover, weather_description, current_hour
            )

    @staticmethod
    def calculate_fallback_light_level(cloud_cover: float, weather_description: str, current_hour: int) -> float:
        """Fallback light calculation if comprehensive method fails"""
        # Simplified version of the original method
        base_light = 100000.0

        # Time of day adjustment
        if 6 <= current_hour <= 18:
            hour_factor = 1.0 - abs(current_hour - 12) / 6.0
            hour_factor = max(0.1, hour_factor)
        else:
            hour_factor = 0.01

        # Cloud cover adjustment
        cloud_factor = 1.0 - (cloud_cover / 100.0) * 0.8

        # Weather condition adjustments
        weather_factor = 1.0
        if any(term in weather_description for term in ['clear', 'sunny']):
            weather_factor = 1.0
        elif any(term in weather_description for term in ['partly', 'scattered']):
            weather_factor = 0.7
        elif any(term in weather_description for term in ['cloudy', 'overcast']):
            weather_factor = 0.3
        elif any(term in weather_description for term in ['rain', 'drizzle', 'shower']):
            weather_factor = 0.2
        elif any(term in weather_description for term in ['storm', 'thunder']):
            weather_factor = 0.1
        elif any(term in weather_description for term in ['fog', 'mist']):
            weather_factor = 0.4

        light_level = base_light * hour_factor * cloud_factor * weather_factor
        return max(10.0, min(120000.0, light_level))


class DataService:
    """Data service for managing real IoT data collection and processing"""

    def __init__(self):
        self.nasa_client = NASAPowerClient()
        self.weather_client = OpenWeatherClient(settings.OPENWEATHER_API_KEY)
        self.sensor_simulator = SensorSimulator()
        self.soil_model = SoilMoistureModel()
        self.data_processor = DataProcessor()
        self.alert_manager = AlertManager()
        self.light_calculator = LightLevelCalculator()
        self.is_collecting = False
        self.collection_errors = 0
        self.max_collection_errors = 5
        self.data_metrics = {
            'total_sensor_readings': 0,
            'total_alerts_generated': 0,
            'last_data_collection': None,
            'active_devices': set(),
            'collection_errors': 0,
            'api_health': {'nasa': True, 'openweather': True},
            'service_uptime': datetime.now(),
            'active_users': set()
        }
        self.collection_task = None

    async def handle_protocol_command(self, command_data: dict):
        """Handle commands received from any communication protocol """
        try:
            if not command_data:
                logger.warning("Received empty command data")
                return {"status": "error", "message": "Empty command data"}

            command_type = command_data.get('command')
            protocol = command_data.get('protocol', 'unknown')
            device_id = command_data.get('device_id', 'unknown')
            user_id = command_data.get('user_id', 1)  # Default to user 1 if not specified

            if not command_type:
                logger.warning("Received command without command type")
                return {"status": "error", "message": "Missing command type"}

            logger.info(f"Received {protocol} command from {device_id}: {command_type} for user {user_id}")

            # Track active devices and users
            self.data_metrics['active_devices'].add(device_id)
            self.data_metrics['active_users'].add(user_id)

            # Handle command types with proper error handling
            if command_type == "refresh_data":
                result = await self._handle_refresh_data(user_id)
                return result

            else:
                logger.warning(f"Unknown command received: {command_type}")
                return {
                    "status": "error",
                    "message": f"Unknown command: {command_type}",
                    "command": command_type,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Error handling protocol command {command_data}: {e}")
            return {
                "status": "error",
                "message": f"Command processing error: {str(e)}",
                "command": command_data.get('command', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }

    async def _handle_refresh_data(self, user_id: int):
        """Handle refresh data command"""
        try:
            logger.info(f"Manual data refresh requested via protocol for user {user_id}")

            # Trigger data collection for specific user
            db = SessionLocal()
            try:
                # Use the synchronous method but don't wait for completion
                import threading
                thread = threading.Thread(
                    target=self._trigger_async_collection,
                    args=(user_id,)
                )
                thread.daemon = True
                thread.start()

                return {
                    "status": "success",
                    "message": f"Data collection triggered for user {user_id}",
                    "command": "refresh_data",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling refresh data command: {e}")
            return {
                "status": "error",
                "message": f"Refresh data failed: {str(e)}",
                "command": "refresh_data",
                "user_id": user_id,
                "timestamp": datetime.now().isoformat()
            }

    def _trigger_async_collection(self, user_id: int):
        """Trigger async data collection in a thread-safe way"""
        try:
            # Create new event loop for the thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            # Run the collection
            loop.run_until_complete(self._collect_real_time_data())
            loop.close()

            logger.info(f"Async data collection completed for user {user_id}")
        except Exception as e:
            logger.error(f"Error in async collection thread: {e}")

    async def handle_incoming_sensor_data(self, sensor_data: dict):
        """Handle sensor data received from communication protocols"""
        try:
            # Validate incoming sensor data
            if not self._validate_sensor_data(sensor_data):
                logger.warning(f"Invalid sensor data received: {sensor_data}")
                return {
                    "status": "error",
                    "message": "Invalid sensor data",
                    "timestamp": datetime.now().isoformat()
                }

            device_id = sensor_data.get('device_id', 'unknown')
            sensor_type = sensor_data.get('sensor_type', 'unknown')
            user_id = sensor_data.get('user_id', 1)  # Default to user 1

            logger.info(
                f"Processing incoming sensor data from {device_id}: {sensor_type} = {sensor_data.get('value')} for user {user_id}")

            # Store in database
            db = SessionLocal()
            try:
                create_sensor_reading(db, sensor_data, user_id)
                self.data_metrics['total_sensor_readings'] += 1
                self.data_metrics['active_devices'].add(device_id)
                self.data_metrics['active_users'].add(user_id)

                # Check for alerts
                try:
                    alerts = self.alert_manager.check_sensor_alerts([sensor_data], db, user_id)
                    await self._broadcast_alerts(alerts)
                except Exception as e:
                    logger.warning(f"Could not check alerts for incoming data: {e}")

                return {
                    "status": "success",
                    "message": "Sensor data processed successfully",
                    "device_id": device_id,
                    "sensor_type": sensor_type,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error storing incoming sensor data: {e}")
                db.rollback()
                return {
                    "status": "error",
                    "message": f"Failed to store sensor data: {str(e)}",
                    "device_id": device_id,
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling incoming sensor data: {e}")
            return {
                "status": "error",
                "message": f"Sensor data processing failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    async def handle_incoming_alert(self, alert_data: dict):
        """Handle incoming alerts from communication protocols"""
        try:
            if not alert_data:
                logger.warning("Received empty alert data")
                return {"status": "error", "message": "Empty alert data"}

            logger.info(f"Processing incoming alert: {alert_data}")

            # Extract alert information with defaults
            alert_type = alert_data.get('type', 'unknown')
            severity = alert_data.get('severity', 'info')
            message = alert_data.get('message', 'No message provided')
            device_id = alert_data.get('device_id', 'unknown')
            user_id = alert_data.get('user_id', 1)
            timestamp = alert_data.get('timestamp', datetime.now().isoformat())
            sensor_type = alert_data.get('sensor_type', 'unknown')

            # Log the incoming alert
            logger.warning(f"Incoming alert received - Type: {alert_type}, Severity: {severity}, "
                           f"Device: {device_id}, User: {user_id}, Sensor: {sensor_type}, Message: {message}")

            # Store alert in database if it's from an external system
            db = SessionLocal()
            try:
                sensor_display = sensor_type.upper().replace('_',
                                                             ' ') + ' SENSOR' if sensor_type != 'unknown' else 'EXTERNAL SENSOR'
                alert_reason = f"{sensor_display} from {device_id}: {message}"

                alert_db_data = {
                    'reason': alert_reason,
                    'severity': severity,
                    'value': alert_data.get('value'),
                    'threshold': alert_data.get('threshold'),
                    'recommendation': alert_data.get('recommendation', 'Check system'),
                    'zone': alert_data.get('zone', 'unknown'),
                    'sensor_type': sensor_type,
                    'device_id': device_id,
                    'timestamp': datetime.fromisoformat(timestamp) if isinstance(timestamp, str) else datetime.now(),
                    'source': 'external_protocol'
                }

                # Create alert in database
                create_alert(db, alert_db_data, user_id)
                self.data_metrics['total_alerts_generated'] += 1
                self.data_metrics['active_users'].add(user_id)

                logger.info(f"Stored external alert in database for user {user_id}: {alert_reason}")

                # Broadcast the alert to other protocols
                broadcast_alert_data = {
                    "alert_id": f"external_alert_{datetime.now().timestamp()}",
                    "message": f"{sensor_display}: {message}",
                    "severity": severity,
                    "timestamp": datetime.now().isoformat(),
                    "value": alert_data.get('value'),
                    "threshold": alert_data.get('threshold'),
                    "device_id": device_id,
                    "source": "external_system",
                    "sensor_type": sensor_type,
                    "user_id": user_id
                }

                try:
                    await protocol_manager.broadcast_alert(broadcast_alert_data)
                except Exception as e:
                    logger.warning(f"Could not broadcast external alert: {e}")

                return {
                    "status": "success",
                    "message": "External alert processed successfully",
                    "alert_reason": alert_reason,
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }

            except Exception as e:
                logger.error(f"Error storing incoming alert: {e}")
                db.rollback()
                return {
                    "status": "error",
                    "message": f"Failed to store alert: {str(e)}",
                    "user_id": user_id,
                    "timestamp": datetime.now().isoformat()
                }
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error handling incoming alert: {e}")
            return {
                "status": "error",
                "message": f"Alert processing failed: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }

    def get_dashboard_data(self, db: Session, user_id: int) -> Dict[str, Any]:
        """Get comprehensive dashboard data for UI"""
        try:
            logger.info(f"Getting dashboard data for user {user_id}")

            # Get recent sensor readings FOR THIS SPECIFIC USER
            recent_readings = get_latest_sensor_readings(db, user_id, hours=1)

            # If no recent data for this user, trigger immediate data collection
            if not recent_readings:
                logger.info(f"No recent data found for user {user_id}, triggering data collection")
                self.collect_real_world_data(db, user_id)

                # Try to get readings again after a brief delay
                import time
                time.sleep(2)
                recent_readings = get_latest_sensor_readings(db, user_id, hours=1)

            # Process into dashboard format
            soil_moisture = {}
            weather_data = {}
            light_level = 0
            device_status = {}
            api_sources = set()

            active_zones = set()

            for reading in recent_readings:
                # Process zone1 and zone2
                if reading.zone not in ['zone1', 'zone2']:
                    continue

                # Track active zones
                active_zones.add(reading.zone)
                api_sources.add(reading.source)

                if reading.sensor_type == 'soil_moisture':
                    soil_moisture[reading.zone] = reading.value
                elif reading.sensor_type == 'temperature':
                    weather_data['temperature'] = reading.value
                elif reading.sensor_type == 'humidity':
                    weather_data['humidity'] = reading.value
                elif reading.sensor_type == 'light_level':
                    light_level = reading.value
                elif reading.sensor_type == 'pressure':
                    weather_data['pressure'] = reading.value
                elif reading.sensor_type == 'wind_speed':
                    weather_data['wind_speed'] = reading.value

                # Track device status
                if reading.device_id:
                    device_status[reading.device_id] = {
                        'last_seen': reading.timestamp.isoformat(),
                        'sensor_type': reading.sensor_type,
                        'value': reading.value,
                        'source': reading.source
                    }

            # Ensure we have a valid light level
            if light_level == 0.0:
                logger.warning(f"Light level is 0.0 for user {user_id}, calculating realistic value")
                light_level = self._calculate_fallback_light_level()
                logger.info(f"Using calculated light level: {light_level} lux")

            # Get user-specific irrigation events
            irrigation_events = get_recent_irrigation_events(db, user_id, days=1)

            # Calculate real water usage FOR THIS USER
            today = datetime.now().date()
            today_water_used = sum(
                event.water_used for event in irrigation_events
                if event.start_time and event.start_time.date() == today
            )

            # Count active zones for this user
            zones_with_data = len([zone for zone in ['zone1', 'zone2'] if zone in active_zones])

            system_metrics = {
                'water_used_today': round(today_water_used, 2),
                'total_water_used': round(sum(event.water_used for event in irrigation_events), 2),
                'energy_saved': 65.0,
                'zones_active': zones_with_data,
                'total_zones': 2,
                'uptime': 99.8,
                'data_points_today': len(recent_readings),
                'api_sources': list(api_sources),
                'data_quality_score': 95.5 if recent_readings else 0.0
            }

            # Get user-specific alerts
            alerts = get_alerts(db, user_id, acknowledged=False, hours=24)
            alert_data = [
                {
                    'id': alert.id,
                    'reason': alert.reason,
                    'severity': alert.severity,
                    'value': alert.value,
                    'recommendation': alert.recommendation,
                    'timestamp': alert.timestamp.isoformat(),
                    'critical': alert.severity == 'critical',
                    'device_id': getattr(alert, 'device_id', 'system'),
                    'message': f"{alert.severity.upper()}: {alert.reason}",
                    'sensor_type': getattr(alert, 'sensor_type', 'unknown')
                }
                for alert in alerts
            ]

            # IRRIGATION DECISIONS for this user
            irrigation_status = {}
            for zone, moisture in soil_moisture.items():
                if moisture < 40.0:
                    irrigation_status[zone] = True
                elif moisture > 85.0:
                    irrigation_status[zone] = False
                else:
                    irrigation_status[zone] = False

            # USER-SPECIFIC WATER USAGE ANALYTICS
            water_stats = {
                "today_water_used": round(today_water_used, 2),
                "weekly_water_used": round(
                    sum(event.water_used for event in get_recent_irrigation_events(db, user_id, days=7)), 2),
                "total_irrigation_events": len(irrigation_events),
                "water_efficiency": 78.5,
                "last_updated": datetime.now().isoformat()
            }

            # Determine data source
            data_source = 'live'
            if 'nasa_power' in api_sources or 'openweather' in api_sources:
                data_source = 'real_world'

            logger.info(
                f"Returning dashboard data for user {user_id}: {len(recent_readings)} readings, {len(alerts)} alerts")

            return {
                'soil_moisture': soil_moisture,
                'weather': weather_data,
                'system_metrics': system_metrics,
                'alerts': alert_data,
                'irrigation_status': irrigation_status,
                'light_level': light_level,
                'device_status': device_status,
                'data_metrics': self.data_metrics,
                'water_usage': water_stats,
                'data_source': data_source,
                'api_sources': list(api_sources),
                'timestamp': datetime.now().isoformat(),
                'data_quality': 'high' if len(recent_readings) > 0 else 'low',
                'user_id': user_id  # Include user ID in response for debugging
            }

        except Exception as e:
            logger.error(f"Error getting dashboard data for user {user_id}: {e}")
            return self._get_fallback_dashboard_data(user_id)

    def _get_fallback_dashboard_data(self, user_id: int) -> Dict[str, Any]:
        """Provide fallback dashboard data when primary data is unavailable"""
        # Calculate realistic light level for fallback
        current_hour = datetime.now().hour
        fallback_light = self.light_calculator.calculate_fallback_light_level(
            cloud_cover=50.0,  # Default partly cloudy
            weather_description="partly cloudy",
            current_hour=current_hour
        )

        return {
            'soil_moisture': {'zone1': 65.0, 'zone2': 55.0},
            'weather': {'temperature': 23.5, 'humidity': 68.0, 'pressure': 101.3, 'wind_speed': 3.2},
            'system_metrics': {
                'water_used_today': 12.5,
                'energy_saved': 85.0,
                'zones_active': 2,
                'uptime': 100.0,
                'data_points_today': 0,
                'data_quality_score': 0.0
            },
            'alerts': [],
            'irrigation_status': {'zone1': False, 'zone2': False},
            'light_level': fallback_light,
            'device_status': {},
            'data_metrics': self.data_metrics,
            'water_usage': {
                'today_water_used': 12.5,
                'weekly_water_used': 45.0,
                'total_irrigation_events': 3,
                'last_updated': datetime.now().isoformat()
            },
            'data_source': 'fallback',
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id
        }

    async def start_periodic_data_collection(self):
        """Start periodic data collection from IoT devices"""
        logger.info("Starting data collection service")

        # Initial data collection for all users
        await self._collect_real_time_data()

        while True:
            try:
                if not self.is_collecting:
                    await self._collect_real_time_data()

                await asyncio.sleep(settings.DATA_COLLECTION_INTERVAL)

            except asyncio.CancelledError:
                logger.info("Data collection task cancelled")
                break
            except Exception as e:
                self.collection_errors += 1
                logger.error(f"Error in data collection cycle {self.collection_errors}: {e}")

                # If too many errors, wait longer before retrying
                wait_time = 300 if self.collection_errors > self.max_collection_errors else 60
                await asyncio.sleep(wait_time)

    async def stop_periodic_data_collection(self):
        """Stop periodic data collection"""
        logger.info("Stopping data collection service")
        if self.collection_task:
            self.collection_task.cancel()
            try:
                await self.collection_task
            except asyncio.CancelledError:
                logger.info("Data collection task stopped successfully")

    def start_background_collection(self):
        """Start data collection in background"""
        try:
            if self.collection_task and not self.collection_task.done():
                logger.info("Data collection already running in background")
                return

            async def run_collection():
                await self.start_periodic_data_collection()

            self.collection_task = asyncio.create_task(run_collection())
            logger.info("Background data collection started")

        except Exception as e:
            logger.error(f"Error starting background collection: {e}")

    async def _collect_real_time_data(self):
        """Collect real-time data from external APIs and process it - for multi-user"""
        try:
            if self.is_collecting:
                logger.info("Data collection already in progress, skipping...")
                return

            self.is_collecting = True
            logger.info("Starting real-time data collection cycle for all users")

            # Get database session
            db = SessionLocal()

            try:
                # Get all active users from database
                users = get_all_users(db)
                if not users:
                    logger.warning("No users found in database")
                    return

                logger.info(f"Collecting data for {len(users)} users")

                # Collect data from external APIs (once for all users)
                external_data = await self._fetch_external_data()

                # Process and store external data for EACH user
                if external_data:
                    for user in users:
                        user_id = user.id
                        logger.info(f"Processing data for user {user_id}")

                        # Track active user
                        self.data_metrics['active_users'].add(user_id)

                        await self._process_external_data(db, external_data, user_id)

                        # Check for alerts for this user
                        await self._check_sensor_alerts(db, user_id)

                # Reset error counter on successful collection
                self.collection_errors = 0
                self.data_metrics['last_data_collection'] = datetime.now()
                logger.info(f"Data collection completed for all users at {self.data_metrics['last_data_collection']}")

            except Exception as e:
                logger.error(f"Error in data collection: {e}")
                db.rollback()
            finally:
                db.close()

        except Exception as e:
            logger.error(f"Error in real-time data collection: {e}")
        finally:
            self.is_collecting = False

    async def _fetch_external_data(self) -> Dict[str, Any]:
        """Fetch data from external APIs with comprehensive error handling"""
        external_data = {}

        try:
            # Get NASA POWER data
            nasa_data = await self._fetch_nasa_data()
            if nasa_data:
                external_data['nasa_power'] = nasa_data
                self.data_metrics['api_health']['nasa'] = True
            else:
                self.data_metrics['api_health']['nasa'] = False

        except Exception as e:
            logger.error(f"Error fetching NASA POWER data: {e}")
            self.data_metrics['api_health']['nasa'] = False

        try:
            # Get current weather data
            if settings.OPENWEATHER_API_KEY and settings.OPENWEATHER_API_KEY != "demo_key":
                weather_data = await self._fetch_weather_data()
                if weather_data:
                    external_data['openweather'] = weather_data
                    self.data_metrics['api_health']['openweather'] = True
                else:
                    self.data_metrics['api_health']['openweather'] = False

        except Exception as e:
            logger.error(f"Error fetching OpenWeather data: {e}")
            self.data_metrics['api_health']['openweather'] = False

        return external_data

    async def _fetch_nasa_data(self) -> Dict[str, Any]:
        """Fetch NASA data with enhanced light level calculation"""
        try:
            loop = asyncio.get_event_loop()

            # Use last week to ensure we get data
            start_date = (datetime.now() - timedelta(days=7)).strftime("%Y%m%d")
            end_date = datetime.now().strftime("%Y%m%d")

            nasa_data = await loop.run_in_executor(
                None,
                self.nasa_client.get_agricultural_data,
                settings.DEFAULT_LATITUDE,
                settings.DEFAULT_LONGITUDE,
                start_date,
                end_date
            )

            if nasa_data and nasa_data.get('data_quality') != 'error':
                logger.info(f"NASA data retrieved for {start_date} to {end_date}")

                # Enhanced data processing with better defaults
                if 'solar_radiation' in nasa_data and nasa_data['solar_radiation'] is not None:
                    nasa_data['solar_radiation'] = max(0.0, float(nasa_data['solar_radiation']))
                    logger.info(f"NASA solar radiation: {nasa_data['solar_radiation']} W/m²")

                    # Calculate light level from solar radiation
                    light_level = self.light_calculator.calculate_solar_radiation_to_lux(
                        nasa_data['solar_radiation']
                    )
                    nasa_data['calculated_light_level'] = light_level
                    logger.info(f"Calculated light level from NASA: {light_level} lux")
                else:
                    # If no solar radiation data, calculate based on time and location
                    current_hour = datetime.now().hour
                    current_minute = datetime.now().minute
                    calculated_light = self.light_calculator.calculate_comprehensive_light_level(
                        cloud_cover=50.0,  # Default cloud cover
                        weather_description="clear",  # Default weather
                        current_hour=current_hour,
                        current_minute=current_minute,
                        solar_radiation=None,
                        latitude=settings.DEFAULT_LATITUDE
                    )
                    nasa_data['calculated_light_level'] = calculated_light
                    logger.info(f"Fallback calculated light level: {calculated_light} lux")

                if 'temperature' in nasa_data and nasa_data['temperature'] is not None:
                    nasa_data['temperature'] = float(nasa_data['temperature'])

                if 'humidity' in nasa_data and nasa_data['humidity'] is not None:
                    nasa_data['humidity'] = max(0.0, min(100.0, float(nasa_data['humidity'])))

                if 'soil_moisture' in nasa_data and nasa_data['soil_moisture'] is not None:
                    nasa_data['soil_moisture'] = max(0.0, min(100.0, float(nasa_data['soil_moisture'])))

                return nasa_data
            else:
                logger.warning("No NASA data available, using calculated light levels")
                # Return minimal data with calculated light
                current_hour = datetime.now().hour
                calculated_light = self.light_calculator.calculate_comprehensive_light_level(
                    cloud_cover=50.0,
                    weather_description="clear",
                    current_hour=current_hour,
                    latitude=settings.DEFAULT_LATITUDE
                )
                return {
                    'calculated_light_level': calculated_light,
                    'temperature': 20.0,
                    'humidity': 60.0,
                    'soil_moisture': 55.0,
                    'data_quality': 'calculated'
                }

        except Exception as e:
            logger.error(f"Error in NASA data fetch: {e}")
            # Return fallback data with calculated light
            current_hour = datetime.now().hour
            calculated_light = self.light_calculator.calculate_fallback_light_level(
                cloud_cover=50.0,
                weather_description="clear",
                current_hour=current_hour
            )
            return {
                'calculated_light_level': calculated_light,
                'temperature': 20.0,
                'humidity': 60.0,
                'soil_moisture': 55.0,
                'data_quality': 'fallback'
            }

    async def _fetch_weather_data(self) -> Dict[str, Any]:
        """Fetch comprehensive weather data with forecast and enhanced light calculation"""
        try:
            loop = asyncio.get_event_loop()

            # Get current weather with error handling
            current_weather = await loop.run_in_executor(
                None,
                self.weather_client.get_current_weather,
                settings.DEFAULT_LATITUDE,
                settings.DEFAULT_LONGITUDE
            )

            # Enhanced validation and light calculation
            if current_weather:
                # Ensure all values are positive and valid
                if 'temperature' in current_weather and current_weather['temperature'] is not None:
                    current_weather['temperature'] = float(current_weather['temperature'])

                if 'humidity' in current_weather and current_weather['humidity'] is not None:
                    current_weather['humidity'] = max(0.0, min(100.0, float(current_weather['humidity'])))

                if 'pressure' in current_weather and current_weather['pressure'] is not None:
                    current_weather['pressure'] = max(800.0, float(current_weather['pressure']))

                if 'wind_speed' in current_weather and current_weather['wind_speed'] is not None:
                    current_weather['wind_speed'] = max(0.0, float(current_weather['wind_speed']))

                if 'cloud_cover' in current_weather and current_weather['cloud_cover'] is not None:
                    current_weather['cloud_cover'] = max(0.0, min(100.0, float(current_weather['cloud_cover'])))
                else:
                    # Default cloud cover if not provided
                    current_weather['cloud_cover'] = 50.0

                if 'precipitation' in current_weather and current_weather['precipitation'] is not None:
                    current_weather['precipitation'] = max(0.0, float(current_weather['precipitation']))

                # Calculate comprehensive light level
                current_time = datetime.now()
                weather_description = current_weather.get('description', 'clear')

                calculated_light = self.light_calculator.calculate_comprehensive_light_level(
                    cloud_cover=current_weather['cloud_cover'],
                    weather_description=weather_description,
                    current_hour=current_time.hour,
                    current_minute=current_time.minute,
                    solar_radiation=None,  # Weather API typically doesn't provide solar radiation
                    latitude=settings.DEFAULT_LATITUDE,
                    current_month=current_time.month
                )

                current_weather['calculated_light_level'] = calculated_light
                logger.info(
                    f"OpenWeather calculated light: {calculated_light} lux (clouds: {current_weather['cloud_cover']}%, weather: '{weather_description}')")

            # Get forecast for irrigation planning
            forecast = await loop.run_in_executor(
                None,
                self.weather_client.get_forecast,
                settings.DEFAULT_LATITUDE,
                settings.DEFAULT_LONGITUDE
            )

            return {
                'current': current_weather,
                'forecast': forecast
            }
        except Exception as e:
            logger.error(f"Error in weather data fetch: {e}")
            # Return fallback data with calculated light
            current_time = datetime.now()
            calculated_light = self.light_calculator.calculate_fallback_light_level(
                cloud_cover=50.0,
                weather_description="clear",
                current_hour=current_time.hour
            )
            return {
                'current': {
                    'temperature': 20.0,
                    'humidity': 60.0,
                    'pressure': 1013.0,
                    'wind_speed': 3.0,
                    'cloud_cover': 50.0,
                    'precipitation': 0.0,
                    'description': 'clear',
                    'calculated_light_level': calculated_light
                },
                'forecast': None
            }

    async def _process_external_data(self, db: Session, external_data: Dict[str, Any], user_id: int):
        """Process and store external data as sensor readings with guaranteed light levels"""
        try:
            sensor_readings = []

            # Process NASA data only if it's valid
            if 'nasa_power' in external_data:
                nasa_data = external_data['nasa_power']
                if nasa_data.get('data_quality') not in ['error', 'invalid']:
                    nasa_readings = self._generate_sensor_readings_from_nasa(nasa_data, user_id)
                    sensor_readings.extend(nasa_readings)
                    logger.info(f"Processed {len(nasa_readings)} NASA readings for user {user_id}")
                else:
                    logger.warning(f"NASA POWER data quality poor for user {user_id}")

            # Process OpenWeather data only if it's valid
            if 'openweather' in external_data:
                weather_data = external_data['openweather']
                if weather_data and weather_data.get('current'):
                    weather_readings = self._generate_sensor_readings_from_weather(weather_data['current'], user_id)
                    sensor_readings.extend(weather_readings)
                    logger.info(f"Processed {len(weather_readings)} OpenWeather readings for user {user_id}")
                else:
                    logger.warning(f"OpenWeather data quality poor for user {user_id}")

            # Ensure we have at least basic light level data
            if not any(r.get('sensor_type') == 'light_level' for r in sensor_readings):
                logger.warning(f"No light level data generated for user {user_id}, creating fallback")
                fallback_light = self._calculate_fallback_light_level()
                light_reading = self._create_light_reading(fallback_light, user_id, 'zone1', 'fallback_calculation')
                sensor_readings.append(light_reading)
                logger.info(f"Added fallback light reading: {fallback_light} lux")

            # Only store valid readings
            valid_readings = [r for r in sensor_readings if r.get('value') is not None]

            for reading in valid_readings:
                create_sensor_reading(db, reading, user_id)
                self.data_metrics['total_sensor_readings'] += 1

            logger.info(f"Stored {len(valid_readings)} valid sensor readings for user {user_id}")

        except Exception as e:
            logger.error(f"Error processing external data for user {user_id}: {e}")
            db.rollback()

    def _generate_sensor_readings_from_nasa(self, nasa_data: Dict[str, Any], user_id: int) -> List[Dict[str, Any]]:
        """Generate sensor readings from NASA POWER data with light levels"""
        readings = []
        base_timestamp = datetime.now()

        if not nasa_data or nasa_data.get('data_quality') == 'error':
            return readings

        try:
            # Use direct values from NASA response
            soil_moisture = nasa_data.get('soil_moisture')
            temperature = nasa_data.get('temperature')
            humidity = nasa_data.get('humidity')
            solar_radiation = nasa_data.get('solar_radiation')
            calculated_light = nasa_data.get('calculated_light_level')

            logger.info(
                f"NASA data for user {user_id} - "
                f"Soil: {soil_moisture}, Temp: {temperature}, "
                f"Solar: {solar_radiation}, Light: {calculated_light}"
            )

            # Create basic readings for zone1 only
            if soil_moisture is not None:
                readings.append({
                    'sensor_type': 'soil_moisture',
                    'value': float(soil_moisture),
                    'zone': 'zone1',
                    'timestamp': base_timestamp,
                    'unit': '%',
                    'device_id': f'nasa_satellite_user_{user_id}',
                    'source': 'nasa_power'
                })

            if temperature is not None:
                readings.append({
                    'sensor_type': 'temperature',
                    'value': float(temperature),
                    'zone': 'zone1',
                    'timestamp': base_timestamp,
                    'unit': 'C',
                    'device_id': f'nasa_satellite_user_{user_id}',
                    'source': 'nasa_power'
                })

            if humidity is not None:
                readings.append({
                    'sensor_type': 'humidity',
                    'value': float(humidity),
                    'zone': 'zone1',
                    'timestamp': base_timestamp,
                    'unit': '%',
                    'device_id': f'nasa_satellite_user_{user_id}',
                    'source': 'nasa_power'
                })

            # LIGHT LEVEL - use calculated value if available, otherwise calculate
            light_value = calculated_light
            if light_value is None and solar_radiation is not None:
                light_value = self.light_calculator.calculate_solar_radiation_to_lux(solar_radiation)
            elif light_value is None:
                # Fallback calculation
                light_value = self._calculate_fallback_light_level()

            if light_value is not None:
                readings.append({
                    'sensor_type': 'light_level',
                    'value': float(light_value),
                    'zone': 'zone1',
                    'timestamp': base_timestamp,
                    'unit': 'lux',
                    'device_id': f'nasa_satellite_user_{user_id}',
                    'source': 'nasa_power'
                })

            logger.info(f"Generated {len(readings)} NASA readings for user {user_id}")
            return readings

        except Exception as e:
            logger.error(f"Error generating NASA readings for user {user_id}: {e}")
            # Return at least light level reading
            fallback_light = self._calculate_fallback_light_level()
            return [self._create_light_reading(fallback_light, user_id, 'zone1', 'nasa_fallback')]

    def _generate_sensor_readings_from_weather(self, weather_data: Dict[str, Any], user_id: int) -> List[
        Dict[str, Any]]:
        """Generate sensor readings from OpenWeather data with light levels"""
        readings = []
        base_timestamp = datetime.now()

        if not weather_data:
            logger.warning(f"OpenWeather: No valid weather data for user {user_id}")
            # Return fallback light reading
            fallback_light = self._calculate_fallback_light_level()
            return [self._create_light_reading(fallback_light, user_id, 'zone1', 'weather_fallback')]

        try:
            # Extract core weather data with defaults
            temperature = weather_data.get('temperature', 20.0)
            humidity = weather_data.get('humidity', 60.0)
            pressure = weather_data.get('pressure', 1013.0)
            wind_speed = weather_data.get('wind_speed', 3.0)
            precipitation = weather_data.get('precipitation', 0)
            cloud_cover = weather_data.get('cloud_cover', 50)
            weather_description = weather_data.get('description', 'clear').lower()
            calculated_light = weather_data.get('calculated_light_level')

            # Use calculated light level if available, otherwise calculate
            if calculated_light is None:
                current_time = datetime.now()
                calculated_light = self.light_calculator.calculate_comprehensive_light_level(
                    cloud_cover=cloud_cover,
                    weather_description=weather_description,
                    current_hour=current_time.hour,
                    current_minute=current_time.minute,
                    latitude=settings.DEFAULT_LATITUDE
                )

            # Create readings for each zone
            zones = ['zone1', 'zone2']

            # LIGHT LEVEL (calculated from weather)
            for zone in zones:
                zone_light = calculated_light
                if zone == 'zone2':
                    zone_light = calculated_light * 0.9  # Slightly different for zone2

                zone_light = max(0.0, float(zone_light))

                readings.append({
                    'sensor_type': 'light_level',
                    'value': zone_light,
                    'zone': zone,
                    'timestamp': base_timestamp,
                    'unit': 'lux',
                    'device_id': f'openweather_user_{user_id}',
                    'source': 'openweather'
                })

            # CALCULATE SOIL MOISTURE FROM WEATHER DATA
            base_moisture = 60.0

            if humidity > 80:
                base_moisture += 15
            elif humidity < 40:
                base_moisture -= 20

            if temperature > 25:
                base_moisture -= 10
            elif temperature < 10:
                base_moisture += 5

            if precipitation > 5:
                base_moisture += 25
            elif precipitation > 1:
                base_moisture += 10

            soil_moisture = max(20.0, min(85.0, base_moisture))

            # SOIL MOISTURE (calculated from weather)
            for zone in zones:
                zone_moisture = soil_moisture
                if zone == 'zone2':
                    zone_moisture = soil_moisture * 0.8

                zone_moisture = max(20.0, min(85.0, zone_moisture))

                readings.append({
                    'sensor_type': 'soil_moisture',
                    'value': float(zone_moisture),
                    'zone': zone,
                    'timestamp': base_timestamp,
                    'unit': '%',
                    'device_id': f'openweather_user_{user_id}',
                    'source': 'openweather'
                })

            # TEMPERATURE
            for zone in zones:
                readings.append({
                    'sensor_type': 'temperature',
                    'value': float(temperature),
                    'zone': zone,
                    'timestamp': base_timestamp,
                    'unit': 'C',
                    'device_id': f'openweather_user_{user_id}',
                    'source': 'openweather'
                })

            # HUMIDITY
            for zone in zones:
                readings.append({
                    'sensor_type': 'humidity',
                    'value': float(humidity),
                    'zone': zone,
                    'timestamp': base_timestamp,
                    'unit': '%',
                    'device_id': f'openweather_user_{user_id}',
                    'source': 'openweather'
                })

            # PRESSURE (convert hPa to kPa)
            pressure_kpa = float(pressure) / 10.0
            for zone in zones:
                readings.append({
                    'sensor_type': 'pressure',
                    'value': pressure_kpa,
                    'zone': zone,
                    'timestamp': base_timestamp,
                    'unit': 'kPa',
                    'device_id': f'openweather_user_{user_id}',
                    'source': 'openweather'
                })

            # WIND SPEED
            for zone in zones:
                readings.append({
                    'sensor_type': 'wind_speed',
                    'value': float(wind_speed),
                    'zone': zone,
                    'timestamp': base_timestamp,
                    'unit': 'm/s',
                    'device_id': f'openweather_user_{user_id}',
                    'source': 'openweather'
                })

            logger.info(f"Generated {len(readings)} OpenWeather readings for user {user_id}")
            return readings

        except Exception as e:
            logger.error(f"Error generating OpenWeather readings for user {user_id}: {e}")
            # Return at least light level reading
            fallback_light = self._calculate_fallback_light_level()
            return [self._create_light_reading(fallback_light, user_id, 'zone1', 'weather_fallback')]

    def _create_light_reading(self, light_level: float, user_id: int, zone: str, source: str) -> Dict[str, Any]:
        """Create a standardized light level reading"""
        return {
            'sensor_type': 'light_level',
            'value': float(light_level),
            'zone': zone,
            'timestamp': datetime.now(),
            'unit': 'lux',
            'device_id': f'{source}_user_{user_id}',
            'source': source
        }

    def _calculate_fallback_light_level(self) -> float:
        """Calculate fallback light level when no external data is available"""
        current_time = datetime.now()
        return self.light_calculator.calculate_fallback_light_level(
            cloud_cover=50.0,
            weather_description="partly cloudy",
            current_hour=current_time.hour
        )

    def _calculate_light_level(self, cloud_cover: float, weather_description: str, current_hour: int) -> float:
        """Legacy method - now uses LightLevelCalculator"""
        return self.light_calculator.calculate_fallback_light_level(
            cloud_cover, weather_description, current_hour
        )

    async def _check_sensor_alerts(self, db: Session, user_id: int):
        """Check for sensor-based alerts"""
        try:
            from ..database.crud import get_latest_sensor_readings, create_alert, get_alerts

            # Only check recent readings (last 30 minutes) to avoid duplicates
            recent_readings = get_latest_sensor_readings(db, user_id, hours=0.5)

            # Get recent unacknowledged alerts to avoid duplicates
            recent_alerts = get_alerts(db, user_id, acknowledged=False, hours=1)
            recent_alert_reasons = [alert.reason for alert in recent_alerts]

            alerts_created = []

            for reading in recent_readings:
                # Skip if this reading is too old
                if (datetime.now() - reading.timestamp).total_seconds() > 3600:  # 1 hour
                    continue

                if reading.source == 'demo':
                    continue

                # Get sensor type for alert messages
                sensor_type_display = reading.sensor_type.upper().replace('_', ' ') + ' SENSOR'

                # Check soil moisture alerts
                if reading.sensor_type == 'soil_moisture':
                    alert_reason = None

                    if reading.value > 85.0:  # Too wet
                        alert_reason = f'{sensor_type_display}: Soil moisture too high in {reading.zone}'
                    elif reading.value < 25.0:  # Critical low
                        alert_reason = f'{sensor_type_display}: Critical low soil moisture in {reading.zone}'
                    elif reading.value < 40.0:  # Warning low
                        alert_reason = f'{sensor_type_display}: Low soil moisture in {reading.zone}'

                    # Check if similar alert already exists
                    if alert_reason and alert_reason not in recent_alert_reasons:
                        severity = 'critical' if reading.value < 25.0 else 'warning'

                        alert_data = {
                            'reason': alert_reason,
                            'severity': severity,
                            'value': reading.value,
                            'threshold': 25.0 if reading.value < 25.0 else (40.0 if reading.value < 40.0 else 85.0),
                            'recommendation': self._get_irrigation_recommendation(reading.value, severity),
                            'zone': reading.zone,
                            'sensor_type': reading.sensor_type,
                            'device_id': reading.device_id,
                            'timestamp': datetime.now()
                        }

                        alert = create_alert(db, alert_data, user_id)
                        alerts_created.append(alert)
                        recent_alert_reasons.append(alert_reason)  # Prevent duplicates in this batch

                        logger.info(f"Created {severity} alert for user {user_id}: {alert_reason} ({reading.value}%)")

                # Check light level alerts
                elif reading.sensor_type == 'light_level':
                    alert_reason = None

                    light_value = max(0.0, float(reading.value))

                    if light_value < 1000.0:  # Very low light
                        alert_reason = f'{sensor_type_display}: Very low light levels in {reading.zone}'
                    elif light_value > 80000.0:  # Very high light
                        alert_reason = f'{sensor_type_display}: Very high light levels in {reading.zone}'

                    # Check if similar alert already exists
                    if alert_reason and alert_reason not in recent_alert_reasons:
                        severity = 'warning'

                        alert_data = {
                            'reason': alert_reason,
                            'severity': severity,
                            'value': light_value,
                            'threshold': 1000.0 if light_value < 1000.0 else 80000.0,
                            'recommendation': self._get_light_recommendation(light_value),
                            'zone': reading.zone,
                            'sensor_type': reading.sensor_type,
                            'device_id': reading.device_id,
                            'timestamp': datetime.now()
                        }

                        alert = create_alert(db, alert_data, user_id)
                        alerts_created.append(alert)
                        recent_alert_reasons.append(alert_reason)

                        logger.info(f"Created {severity} alert for user {user_id}: {alert_reason} ({light_value} lux)")

            if alerts_created:
                logger.info(f"Created {len(alerts_created)} new alerts for user {user_id} (duplicates prevented)")
            return alerts_created

        except Exception as e:
            logger.error(f"Error checking sensor alerts for user {user_id}: {e}")
            return []

    def _get_irrigation_recommendation(self, moisture: float, severity: str) -> str:
        """Get appropriate irrigation recommendation"""
        if moisture > 85.0:
            return "Reduce irrigation - Risk of root diseases"
        elif moisture < 25.0:
            return "EMERGENCY IRRIGATION REQUIRED - Plants at risk"
        elif moisture < 40.0:
            return "Schedule irrigation within 24 hours"
        else:
            return "Moisture levels optimal"

    def _get_light_recommendation(self, light_level: float) -> str:
        """Get appropriate light level recommendation"""
        if light_level < 1000.0:
            return "Consider supplemental lighting for plant growth"
        elif light_level > 80000.0:
            return "High light levels - monitor for plant stress"
        elif light_level < 10000.0:
            return "Low light conditions - plants may grow slowly"
        else:
            return "Light levels optimal for plant growth"

    def collect_real_world_data(self, db: Session, user_id: int):
        """Synchronous wrapper for real-time data collection"""
        try:
            logger.info(f"Manual data refresh requested via API for user {user_id}")

            # Track active user
            self.data_metrics['active_users'].add(user_id)

            # For API calls, trigger the async collection but don't wait for it
            async def trigger_collection():
                await self._collect_real_time_data()

            # Create a task but don't wait for completion
            try:
                loop = asyncio.get_running_loop()
                # If there's a running loop, create a task
                asyncio.create_task(trigger_collection())
            except RuntimeError:
                # No running loop, create a new one and run
                asyncio.run(trigger_collection())

            return {"status": "success", "message": "Data collection triggered"}

        except Exception as e:
            logger.error(f"Error in collect_real_world_data: {e}")
            return {"status": "error", "message": str(e)}

    def get_service_metrics(self) -> Dict[str, Any]:
        """Get data service metrics for monitoring"""
        uptime = datetime.now() - self.data_metrics['service_uptime']

        base_metrics = {
            **self.data_metrics,
            'service_status': 'running' if not self.is_collecting else 'collecting',
            'collection_interval': settings.DATA_COLLECTION_INTERVAL,
            'active_device_count': len(self.data_metrics['active_devices']),
            'active_user_count': len(self.data_metrics['active_users']),
            'collection_errors': self.collection_errors,
            'uptime_seconds': int(uptime.total_seconds()),
            'uptime_human': str(uptime).split('.')[0]
        }

        return base_metrics

    def _validate_sensor_data(self, sensor_data: dict) -> bool:
        """Validate incoming sensor data"""
        try:
            required_fields = ['sensor_type', 'value', 'timestamp']
            for field in required_fields:
                if field not in sensor_data:
                    logger.warning(f"Missing required field in sensor data: {field}")
                    return False

            # Validate value is numeric
            try:
                float(sensor_data['value'])
            except (ValueError, TypeError):
                logger.warning(f"Invalid sensor value: {sensor_data['value']}")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating sensor data: {e}")
            return False

    async def _broadcast_alerts(self, alerts: List[Any]):
        """Broadcast alerts to communication protocols"""
        try:
            if not alerts:
                return

            for alert in alerts:
                alert_data = {
                    "alert_id": f"alert_{alert.id}",
                    "message": alert.reason,
                    "severity": alert.severity,
                    "timestamp": alert.timestamp.isoformat(),
                    "value": alert.value,
                    "threshold": alert.threshold,
                    "device_id": getattr(alert, 'device_id', 'system'),
                    "source": "data_service",
                    "sensor_type": getattr(alert, 'sensor_type', 'unknown'),
                    "user_id": getattr(alert, 'user_id', 1)
                }

                try:
                    await protocol_manager.broadcast_alert(alert_data)
                except Exception as e:
                    logger.warning(f"Could not broadcast alert {alert.id}: {e}")

        except Exception as e:
            logger.error(f"Error broadcasting alerts: {e}")