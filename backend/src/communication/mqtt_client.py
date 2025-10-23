<<<<<<< HEAD
import paho.mqtt.client as mqtt
import json
import logging
import asyncio
from typing import Callable, Dict, Any
from ..core.config import settings

logger = logging.getLogger(__name__)


class MQTTClient:
    def __init__(self):
        self.client = None
        self.is_connected = False
        self.message_handlers = {}
        self._connect_callbacks = []
        self._reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def connect(self):
        """Connect to MQTT broker"""
        try:
            self.client = mqtt.Client()
            self.client.reconnect_delay_set(min_delay=1, max_delay=30)

            # Set credentials
            if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
                self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)

            # Set callbacks
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect

            # Set last will and testament
            self.client.will_set(
                settings.MQTT_TOPIC_SYSTEM_STATUS,
                json.dumps({"status": "offline", "timestamp": ""}),
                qos=1,
                retain=True
            )

            # Connect to broker with timeout
            self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
            self.client.loop_start()

            logger.info(f"MQTT client connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}")

            # Wait for connection with timeout
            await asyncio.sleep(2)
            if self.is_connected:
                return True
            else:
                logger.error("MQTT connection timeout")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            return False

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.is_connected = True
            self._reconnect_attempts = 0
            logger.info("MQTT client connected successfully")

            # Subscribe to topics
            self._subscribe_to_topics()

            # Publish online status
            asyncio.create_task(self.publish_system_status({
                "status": "online",
                "timestamp": ""
            }))

            # Notify connect callbacks
            for callback in self._connect_callbacks:
                callback()
        else:
            logger.error(f"MQTT connection failed with code: {rc}")
            self.is_connected = False
            self._handle_connection_failure()

    def _handle_connection_failure(self):
        """Handle connection failure with exponential backoff"""
        self._reconnect_attempts += 1
        if self._reconnect_attempts <= self.max_reconnect_attempts:
            delay = min(2 ** self._reconnect_attempts, 30)
            logger.info(f"Reconnecting in {delay} seconds (attempt {self._reconnect_attempts})")
            asyncio.create_task(self._delayed_reconnect(delay))

    async def _delayed_reconnect(self, delay: int):
        """Attempt reconnection after delay"""
        await asyncio.sleep(delay)
        if not self.is_connected:
            await self.connect()

    def _on_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.is_connected = False
        if rc != 0:
            logger.warning(f"MQTT unexpected disconnection (code: {rc})")
            self._handle_connection_failure()
        else:
            logger.info("MQTT client disconnected")

    def _on_message(self, client, userdata, msg):
        """Callback when message is received"""
        try:
            topic = msg.topic
            payload = msg.payload.decode()

            logger.debug(f"MQTT message received on {topic}")

            # Parse JSON payload
            data = json.loads(payload)

            # Call appropriate handler
            if topic in self.message_handlers:
                for handler in self.message_handlers[topic]:
                    handler(data)
            else:
                logger.warning(f"No handler registered for topic: {topic}")

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON payload on topic {topic}")
        except Exception as e:
            logger.error(f"Error processing MQTT message: {e}")

    def _subscribe_to_topics(self):
        """Subscribe to all required topics"""
        topics = [
            (settings.MQTT_TOPIC_COMMANDS, 0),
            (f"{settings.MQTT_TOPIC_SENSOR_DATA}/+", 0),
        ]

        for topic, qos in topics:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Subscribed to MQTT topic: {topic}")
            else:
                logger.error(f"Failed to subscribe to {topic}: {result}")

    def register_message_handler(self, topic: str, handler: Callable):
        """Register a handler for a specific topic"""
        if topic not in self.message_handlers:
            self.message_handlers[topic] = []
        self.message_handlers[topic].append(handler)
        logger.info(f"Registered handler for MQTT topic: {topic}")

    def register_connect_callback(self, callback: Callable):
        """Register callback to be called when connected"""
        self._connect_callbacks.append(callback)

    async def publish_sensor_data(self, sensor_data: Dict[str, Any]):
        """Publish sensor data to MQTT with production reliability"""
        if not self.is_connected:
            logger.warning("MQTT client not connected, cannot publish sensor data")
            return False

        try:
            payload = json.dumps({
                **sensor_data,
                "timestamp": sensor_data.get("timestamp"),
                "sensor_type": sensor_data.get("sensor_type", "unknown"),
                "protocol": "mqtt"
            })

            result = self.client.publish(settings.MQTT_TOPIC_SENSOR_DATA, payload, qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.debug(f"Published sensor data to MQTT: {sensor_data.get('sensor_type')}")
                return True
            else:
                logger.error(f"Failed to publish sensor data: MQTT error {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Failed to publish sensor data to MQTT: {e}")
            return False

    async def publish_alert(self, alert_data: Dict[str, Any]):
        """Publish alert to MQTT with production reliability"""
        if not self.is_connected:
            logger.warning("MQTT client not connected, cannot publish alert")
            return False

        try:
            payload = json.dumps({
                **alert_data,
                "timestamp": alert_data.get("timestamp"),
                "severity": alert_data.get("severity", "warning"),
                "protocol": "mqtt"
            })

            result = self.client.publish(settings.MQTT_TOPIC_ALERTS, payload, qos=2, retain=True)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"Published alert to MQTT: {alert_data.get('message')}")
                return True
            else:
                logger.error(f"Failed to publish alert: MQTT error {result.rc}")
                return False

        except Exception as e:
            logger.error(f"Failed to publish alert to MQTT: {e}")
            return False

    async def publish_system_status(self, status_data: Dict[str, Any]):
        """Publish system status to MQTT"""
        if not self.is_connected:
            return False

        try:
            payload = json.dumps({
                **status_data,
                "protocol": "mqtt"
            })
            result = self.client.publish(settings.MQTT_TOPIC_SYSTEM_STATUS, payload, qos=1, retain=True)
            return result.rc == mqtt.MQTT_ERR_SUCCESS

        except Exception as e:
            logger.error(f"Failed to publish system status to MQTT: {e}")
            return False

    async def disconnect(self):
        """Disconnect from MQTT broker gracefully"""
        try:
            if self.client:
                # Publish offline status
                await self.publish_system_status({
                    "status": "offline",
                    "timestamp": ""
                })

                self.client.loop_stop()
                self.client.disconnect()
                logger.info("MQTT client disconnected gracefully")
        except Exception as e:
            logger.error(f"Error disconnecting MQTT client: {e}")
=======
# import paho.mqtt.client as mqtt
# import json
# import logging
# import asyncio
# from typing import Callable, Dict, Any
# from ..core.config import settings
#
# logger = logging.getLogger(__name__)
#
#
# class MQTTClient:
#     def __init__(self):
#         self.client = None
#         self.is_connected = False
#         self.message_handlers = {}
#         self._connect_callbacks = []
#         self._reconnect_attempts = 0
#         self.max_reconnect_attempts = 5
#
#     async def connect(self):
#         """Connect to MQTT broker"""
#         try:
#             self.client = mqtt.Client()
#             self.client.reconnect_delay_set(min_delay=1, max_delay=30)
#
#             # Set credentials
#             if settings.MQTT_USERNAME and settings.MQTT_PASSWORD:
#                 self.client.username_pw_set(settings.MQTT_USERNAME, settings.MQTT_PASSWORD)
#
#             # Set callbacks
#             self.client.on_connect = self._on_connect
#             self.client.on_message = self._on_message
#             self.client.on_disconnect = self._on_disconnect
#
#             # Set last will and testament
#             self.client.will_set(
#                 settings.MQTT_TOPIC_SYSTEM_STATUS,
#                 json.dumps({"status": "offline", "timestamp": ""}),
#                 qos=1,
#                 retain=True
#             )
#
#             # Connect to broker with timeout
#             self.client.connect(settings.MQTT_BROKER, settings.MQTT_PORT, 60)
#             self.client.loop_start()
#
#             logger.info(f"MQTT client connecting to {settings.MQTT_BROKER}:{settings.MQTT_PORT}")
#
#             # Wait for connection with timeout
#             await asyncio.sleep(2)
#             if self.is_connected:
#                 return True
#             else:
#                 logger.error("MQTT connection timeout")
#                 return False
#
#         except Exception as e:
#             logger.error(f"Failed to connect to MQTT broker: {e}")
#             return False
#
#     def _on_connect(self, client, userdata, flags, rc):
#         """Callback when connected to MQTT broker"""
#         if rc == 0:
#             self.is_connected = True
#             self._reconnect_attempts = 0
#             logger.info("MQTT client connected successfully")
#
#             # Subscribe to topics
#             self._subscribe_to_topics()
#
#             # Publish online status
#             asyncio.create_task(self.publish_system_status({
#                 "status": "online",
#                 "timestamp": ""
#             }))
#
#             # Notify connect callbacks
#             for callback in self._connect_callbacks:
#                 callback()
#         else:
#             logger.error(f"MQTT connection failed with code: {rc}")
#             self.is_connected = False
#             self._handle_connection_failure()
#
#     def _handle_connection_failure(self):
#         """Handle connection failure with exponential backoff"""
#         self._reconnect_attempts += 1
#         if self._reconnect_attempts <= self.max_reconnect_attempts:
#             delay = min(2 ** self._reconnect_attempts, 30)
#             logger.info(f"Reconnecting in {delay} seconds (attempt {self._reconnect_attempts})")
#             asyncio.create_task(self._delayed_reconnect(delay))
#
#     async def _delayed_reconnect(self, delay: int):
#         """Attempt reconnection after delay"""
#         await asyncio.sleep(delay)
#         if not self.is_connected:
#             await self.connect()
#
#     def _on_disconnect(self, client, userdata, rc):
#         """Callback when disconnected from MQTT broker"""
#         self.is_connected = False
#         if rc != 0:
#             logger.warning(f"MQTT unexpected disconnection (code: {rc})")
#             self._handle_connection_failure()
#         else:
#             logger.info("MQTT client disconnected")
#
#     def _on_message(self, client, userdata, msg):
#         """Callback when message is received"""
#         try:
#             topic = msg.topic
#             payload = msg.payload.decode()
#
#             logger.debug(f"MQTT message received on {topic}")
#
#             # Parse JSON payload
#             data = json.loads(payload)
#
#             # Call appropriate handler
#             if topic in self.message_handlers:
#                 for handler in self.message_handlers[topic]:
#                     handler(data)
#             else:
#                 logger.warning(f"No handler registered for topic: {topic}")
#
#         except json.JSONDecodeError:
#             logger.error(f"Invalid JSON payload on topic {topic}")
#         except Exception as e:
#             logger.error(f"Error processing MQTT message: {e}")
#
#     def _subscribe_to_topics(self):
#         """Subscribe to all required topics"""
#         topics = [
#             (settings.MQTT_TOPIC_COMMANDS, 0),
#             (f"{settings.MQTT_TOPIC_SENSOR_DATA}/+", 0),
#         ]
#
#         for topic, qos in topics:
#             result = self.client.subscribe(topic, qos)
#             if result[0] == mqtt.MQTT_ERR_SUCCESS:
#                 logger.info(f"Subscribed to MQTT topic: {topic}")
#             else:
#                 logger.error(f"Failed to subscribe to {topic}: {result}")
#
#     def register_message_handler(self, topic: str, handler: Callable):
#         """Register a handler for a specific topic"""
#         if topic not in self.message_handlers:
#             self.message_handlers[topic] = []
#         self.message_handlers[topic].append(handler)
#         logger.info(f"Registered handler for MQTT topic: {topic}")
#
#     def register_connect_callback(self, callback: Callable):
#         """Register callback to be called when connected"""
#         self._connect_callbacks.append(callback)
#
#     async def publish_sensor_data(self, sensor_data: Dict[str, Any]):
#         """Publish sensor data to MQTT with production reliability"""
#         if not self.is_connected:
#             logger.warning("MQTT client not connected, cannot publish sensor data")
#             return False
#
#         try:
#             payload = json.dumps({
#                 **sensor_data,
#                 "timestamp": sensor_data.get("timestamp"),
#                 "sensor_type": sensor_data.get("sensor_type", "unknown"),
#                 "protocol": "mqtt"
#             })
#
#             result = self.client.publish(settings.MQTT_TOPIC_SENSOR_DATA, payload, qos=1)
#
#             if result.rc == mqtt.MQTT_ERR_SUCCESS:
#                 logger.debug(f"Published sensor data to MQTT: {sensor_data.get('sensor_type')}")
#                 return True
#             else:
#                 logger.error(f"Failed to publish sensor data: MQTT error {result.rc}")
#                 return False
#
#         except Exception as e:
#             logger.error(f"Failed to publish sensor data to MQTT: {e}")
#             return False
#
#     async def publish_alert(self, alert_data: Dict[str, Any]):
#         """Publish alert to MQTT with production reliability"""
#         if not self.is_connected:
#             logger.warning("MQTT client not connected, cannot publish alert")
#             return False
#
#         try:
#             payload = json.dumps({
#                 **alert_data,
#                 "timestamp": alert_data.get("timestamp"),
#                 "severity": alert_data.get("severity", "warning"),
#                 "protocol": "mqtt"
#             })
#
#             result = self.client.publish(settings.MQTT_TOPIC_ALERTS, payload, qos=2, retain=True)
#
#             if result.rc == mqtt.MQTT_ERR_SUCCESS:
#                 logger.info(f"Published alert to MQTT: {alert_data.get('message')}")
#                 return True
#             else:
#                 logger.error(f"Failed to publish alert: MQTT error {result.rc}")
#                 return False
#
#         except Exception as e:
#             logger.error(f"Failed to publish alert to MQTT: {e}")
#             return False
#
#     async def publish_system_status(self, status_data: Dict[str, Any]):
#         """Publish system status to MQTT"""
#         if not self.is_connected:
#             return False
#
#         try:
#             payload = json.dumps({
#                 **status_data,
#                 "protocol": "mqtt"
#             })
#             result = self.client.publish(settings.MQTT_TOPIC_SYSTEM_STATUS, payload, qos=1, retain=True)
#             return result.rc == mqtt.MQTT_ERR_SUCCESS
#
#         except Exception as e:
#             logger.error(f"Failed to publish system status to MQTT: {e}")
#             return False
#
#     async def disconnect(self):
#         """Disconnect from MQTT broker gracefully"""
#         try:
#             if self.client:
#                 # Publish offline status
#                 await self.publish_system_status({
#                     "status": "offline",
#                     "timestamp": ""
#                 })
#
#                 self.client.loop_stop()
#                 self.client.disconnect()
#                 logger.info("MQTT client disconnected gracefully")
#         except Exception as e:
#             logger.error(f"Error disconnecting MQTT client: {e}")
>>>>>>> b46545bf3 (Add build and dist folders)
