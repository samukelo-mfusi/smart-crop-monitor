import asyncio
import logging
import time
from typing import Dict, Any
from .mqtt_client import MQTTClient
from .http_server import HTTPServer
from ..core.config import settings

logger = logging.getLogger(__name__)


class ProtocolManager:
    def __init__(self):
        self.mqtt_client = MQTTClient()
        self.http_server = HTTPServer()
        self.active_protocols = []
        self.start_time = time.time()

    async def initialize_protocols(self):
        """Initialize all communication protocols"""
        protocols = []

        # Initialize HTTP
        if settings.HTTP_ENABLED:
            if await self.http_server.start_server():
                protocols.append('http')
                logger.info("HTTP protocol initialized")

        self.active_protocols = protocols

        if protocols:
            logger.info(f"Active protocols: {protocols}")
            return True
        else:
            logger.error("No communication protocols initialized")
            return False

    def register_message_handler(self, message_type: str, handler):
        """Register handler for all protocols"""
        if settings.HTTP_ENABLED:
            self.http_server.register_message_handler(message_type, handler)

    async def broadcast_sensor_data(self, sensor_data: Dict[str, Any]):
        """Broadcast sensor data through all protocols"""
        tasks = []
        if 'http' in self.active_protocols:
            tasks.append(self.http_server.broadcast_sensor_data(sensor_data))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast alert through all protocols"""
        tasks = []
        if 'http' in self.active_protocols:
            tasks.append(self.http_server.broadcast_alert(alert_data))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status"""
        if 'http' in self.active_protocols:
            await self.http_client.publish_system_status(status_data)

    def get_protocol_status(self) -> Dict[str, Any]:
        """Get status of all protocols"""
        return {
            'mqtt': {
                'enabled': settings.MQTT_ENABLED,
                'connected': self.mqtt_client.is_connected if settings.MQTT_ENABLED else False
            },
            'http': {
                'enabled': settings.HTTP_ENABLED,
                'port': settings.HTTP_PORT
            },
            'active_protocols': self.active_protocols,
            'uptime': time.time() - self.start_time
        }

    async def shutdown(self):
        """Shutdown all protocols"""
        shutdown_tasks = []
        if settings.HTTP_ENABLED:
            shutdown_tasks.append(self.http_server.shutdown())
        if shutdown_tasks:
            await asyncio.gather(*shutdown_tasks, return_exceptions=True)


# Global protocol manager instance
protocol_manager = ProtocolManager()
