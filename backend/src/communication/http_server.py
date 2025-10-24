from aiohttp import web
import json
import logging
import time
from typing import Dict, Any, Callable, Set
from ..core.config import settings

logger = logging.getLogger(__name__)


class HTTPServer:
    def __init__(self):
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.message_handlers = {}
        self.websockets: Set[web.WebSocketResponse] = set()
        self.start_time = time.time()

    async def start_server(self):
        """Start HTTP server"""
        try:
            # Add routes
            self.app.router.add_post('/sensor-data', self.handle_sensor_data)
            self.app.router.add_post('/alerts', self.handle_alerts)
            self.app.router.add_get('/health', self.handle_health)
            self.app.router.add_post('/commands', self.handle_commands)
            self.app.router.add_get('/system/status', self.handle_system_status)

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, '0.0.0.0', settings.HTTP_PORT)
            await self.site.start()

            logger.info(f"HTTP server started on port {settings.HTTP_PORT}")
            return True

        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False

    async def handle_sensor_data(self, request):
        """Handle incoming sensor data via HTTP"""
        try:
            data = await request.json()

            # Validate required fields
            if not all(k in data for k in ['sensor_type', 'value', 'timestamp']):
                return web.Response(
                    text=json.dumps({"error": "Missing required fields"}),
                    status=400,
                    content_type='application/json'
                )

            logger.info(f"HTTP sensor data received: {data.get('sensor_type')}")

            # Process through handlers
            await self._call_handlers('sensor_data', data)

            return web.Response(
                text=json.dumps({
                    "status": "success",
                    "protocol": "http",
                    "message": "Sensor data processed"
                }),
                content_type='application/json'
            )
        except json.JSONDecodeError:
            return web.Response(
                text=json.dumps({"error": "Invalid JSON"}),
                status=400,
                content_type='application/json'
            )
        except Exception as e:
            logger.error(f"Error handling HTTP sensor data: {e}")
            return web.Response(
                text=json.dumps({"error": "Internal server error"}),
                status=500,
                content_type='application/json'
            )

    async def handle_alerts(self, request):
        """Handle incoming alerts via HTTP"""
        try:
            data = await request.json()

            if not all(k in data for k in ['message', 'severity', 'timestamp']):
                return web.Response(
                    text=json.dumps({"error": "Missing required fields"}),
                    status=400,
                    content_type='application/json'
                )

            logger.info(f"HTTP alert received: {data.get('message')}")

            await self._call_handlers('alerts', data)

            return web.Response(
                text=json.dumps({
                    "status": "success",
                    "protocol": "http",
                    "message": "Alert processed"
                }),
                content_type='application/json'
            )
        except Exception as e:
            logger.error(f"Error handling HTTP alert: {e}")
            return web.Response(
                text=json.dumps({"error": str(e)}),
                status=500,
                content_type='application/json'
            )

    async def handle_commands(self, request):
        """Handle incoming commands via HTTP"""
        try:
            data = await request.json()

            if 'type' not in data:
                return web.Response(
                    text=json.dumps({"error": "Missing command type"}),
                    status=400,
                    content_type='application/json'
                )

            logger.info(f"HTTP command received: {data.get('type')}")

            await self._call_handlers('commands', data)

            return web.Response(
                text=json.dumps({
                    "status": "success",
                    "protocol": "http",
                    "message": "Command processed"
                }),
                content_type='application/json'
            )
        except Exception as e:
            logger.error(f"Error handling HTTP command: {e}")
            return web.Response(
                text=json.dumps({"error": str(e)}),
                status=500,
                content_type='application/json'
            )

    async def handle_system_status(self, request):
        """System status endpoint"""
        return web.Response(
            text=json.dumps({
                "status": "operational",
                "protocol": "http",
                "server": "running"
            }),
            content_type='application/json'
        )

    async def handle_health(self, request):
        """Health check endpoint"""
        return web.Response(
            text=json.dumps({
                "status": "healthy",
                "protocol": "http",
                "server": "running"
            }),
            content_type='application/json'
        )

    async def _call_handlers(self, handler_type: str, data: Dict[str, Any]):
        """Call registered handlers for specific message type"""
        if handler_type in self.message_handlers:
            for handler in self.message_handlers[handler_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error in HTTP handler: {e}")

    def register_message_handler(self, handler_type: str, handler: Callable):
        """Register handler for specific message type"""
        if handler_type not in self.message_handlers:
            self.message_handlers[handler_type] = []
        self.message_handlers[handler_type].append(handler)
        logger.info(f"Registered HTTP handler for: {handler_type}")

    async def broadcast_sensor_data(self, sensor_data: Dict[str, Any]):
        """Broadcast sensor data via HTTP (for clients that poll)"""
        logger.debug(f"HTTP would broadcast sensor data: {sensor_data.get('sensor_type')}")
        return True

    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast alert via HTTP"""
        logger.debug(f"HTTP would broadcast alert: {alert_data.get('message')}")
        return True

    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status via HTTP"""
        logger.debug(f"HTTP would broadcast system status: {status_data}")
        return True

    async def shutdown(self):
        """Shutdown HTTP server gracefully"""
        try:
            if self.site:
                await self.site.stop()
            if self.runner:
                await self.runner.cleanup()
            logger.info("HTTP server shutdown complete")
        except Exception as e:
            logger.error(f"Error shutting down HTTP server: {e}")
