import asyncio
import logging
import time
from typing import Dict, Any

import self

# from .mqtt_client import MQTTClient
from .http_server import HTTPServer
# from .coap_server import CoAPServer
from ..core.config import settings

logger = logging.getLogger(__name__)


class ProtocolManager:
    def __init__(self):
        # self.mqtt_client = MQTTClient()
        self.http_server = HTTPServer()
        # self.coap_server = CoAPServer()
        self.active_protocols = []
        self.start_time = time.time()

    async def initialize_protocols(self):
        """Initialize all communication protocols"""
        protocols = []

        # Initialize MQTT
        # if settings.MQTT_ENABLED:
        #     if await self.mqtt_client.connect():
        #         protocols.append('mqtt')
        #         logger.info("MQTT protocol initialized")

        # Initialize HTTP
        if settings.HTTP_ENABLED:
            if await self.http_server.start_server():
                protocols.append('http')
                logger.info("HTTP protocol initialized")

        # Initialize CoAP
        # if settings.COAP_ENABLED:
        #     if await self.coap_server.start_server():
        #         protocols.append('coap')
        #         logger.info("CoAP protocol initialized")

        self.active_protocols = protocols

        if protocols:
            logger.info(f"Active protocols: {protocols}")
            return True
        else:
            logger.error("No communication protocols initialized")
            return False

    def register_message_handler(self, message_type: str, handler):
        """Register handler for all protocols"""
        # if settings.MQTT_ENABLED and message_type == 'commands':
        #     self.mqtt_client.register_message_handler(
        #         settings.MQTT_TOPIC_COMMANDS,
        #         handler
        #     )

        if settings.HTTP_ENABLED:
            self.http_server.register_message_handler(message_type, handler)

        # if settings.COAP_ENABLED:
        #     self.coap_server.register_message_handler(message_type, handler)

    async def broadcast_sensor_data(self, sensor_data: Dict[str, Any]):
        """Broadcast sensor data through all protocols"""
        tasks = []

        # if 'mqtt' in self.active_protocols:
        #     tasks.append(self.mqtt_client.publish_sensor_data(sensor_data))

        if 'http' in self.active_protocols:
            tasks.append(self.http_server.broadcast_sensor_data(sensor_data))

        # if 'coap' in self.active_protocols:
        #     tasks.append(self.coap_server.publish_sensor_data(sensor_data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast alert through all protocols"""
        tasks = []

        # if 'mqtt' in self.active_protocols:
        #     tasks.append(self.mqtt_client.publish_alert(alert_data))

        if 'http' in self.active_protocols:
            tasks.append(self.http_server.broadcast_alert(alert_data))

        # if 'coap' in self.active_protocols:
        #     tasks.append(self.coap_server.publish_alert(alert_data))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status"""
        # if 'mqtt' in self.active_protocols:
        #     await self.mqtt_client.publish_system_status(status_data)

    def get_protocol_status(self) -> Dict[str, Any]:
        """Get status of all protocols"""
        return {
            # 'mqtt': {
            #     'enabled': settings.MQTT_ENABLED,
            #     'connected': self.mqtt_client.is_connected if settings.MQTT_ENABLED else False
            # },
            'http': {
                'enabled': settings.HTTP_ENABLED,
                'port': settings.HTTP_PORT
            },
            # 'coap': {
                # 'enabled': settings.COAP_ENABLED,
                # 'running': self.coap_server.is_running if settings.COAP_ENABLED else False,
                # 'active_clients': len(
                    # self.coap_server.observation_manager.get_active_clients()) if settings.COAP_ENABLED else 0
            # },
            'active_protocols': self.active_protocols,
            'uptime': time.time() - self.start_time
        }

    async def shutdown(self):
        """Shutdown all protocols"""
        shutdown_tasks = []

        # if settings.MQTT_ENABLED:
        #     shutdown_tasks.append(self.mqtt_client.disconnect())

        if settings.HTTP_ENABLED:
            shutdown_tasks.append(self.http_server.shutdown())

        if settings.COAP_ENABLED:
            shutdown_tasks.append(self.coap_server.shutdown())

        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)


# Global protocol manager instance
protocol_manager = ProtocolManager()