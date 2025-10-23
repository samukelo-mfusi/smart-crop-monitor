import asyncio
import json
import logging
import time
from typing import Dict, Any, Callable, Set
from aiohttp import web, WSMsgType

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
            self.app.router.add_post('/api/sensor-data', self.handle_sensor_data)
            self.app.router.add_post('/api/alerts', self.handle_alerts)
            self.app.router.add_get('/api/health', self.handle_health)
            self.app.router.add_post('/api/commands', self.handle_commands)
            self.app.router.add_get('/api/system/status', self.handle_system_status)
            self.app.router.add_get('/api/ws', self.handle_websocket) # WebSocket endpoint
            
            # CORS setup for production
            async def cors_middleware(app, handler):
                async def middleware_handler(request):
                    if request.method == 'OPTIONS':
                        response = web.Response()
                    else:
                        response = await handler(request)
                    
                    response.headers['Access-Control-Allow-Origin'] = '*'
                    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
                    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
                    return response
                return middleware_handler

            self.app.middlewares.append(cors_middleware)

            self.runner = web.AppRunner(self.app)
            await self.runner.setup()

            self.site = web.TCPSite(self.runner, '0.0.0.0', settings.HTTP_PORT)
            await self.site.start()

            logger.info(f"HTTP server started on port {settings.HTTP_PORT}")
            return True

        except Exception as e:
            logger.error(f"Failed to start HTTP server: {e}")
            return False

    async def handle_websocket(self, request):
        """Handle WebSocket connections for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        
        self.websockets.add(ws)
        client_count = len(self.websockets)
        logger.info(f"WebSocket client connected. Total clients: {client_count}")

        try:
            # Send welcome message with current system status
            welcome_msg = {
                'type': 'connection_established',
                'message': 'Connected to sensor data stream',
                'client_count': client_count,
                'timestamp': time.time()
            }
            await ws.send_json(welcome_msg)

            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._handle_websocket_message(ws, data)
                    except json.JSONDecodeError:
                        error_msg = {
                            'type': 'error',
                            'message': 'Invalid JSON format',
                            'timestamp': time.time()
                        }
                        await ws.send_json(error_msg)
                        logger.warning("Invalid JSON received via WebSocket")
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            self.websockets.remove(ws)
            logger.info(f"WebSocket client disconnected. Total clients: {len(self.websockets)}")

        return ws

    async def _handle_websocket_message(self, ws: web.WebSocketResponse, data: Dict[str, Any]):
        """Handle incoming WebSocket messages"""
        message_type = data.get('type')
        
        if message_type == 'subscribe':
            # Handle subscription requests
            channels = data.get('channels', [])
            response = {
                'type': 'subscription_confirmed',
                'channels': channels,
                'timestamp': time.time()
            }
            await ws.send_json(response)
            logger.info(f"WebSocket client subscribed to channels: {channels}")
            
        elif message_type == 'ping':
            # Handle ping/pong for connection health
            response = {
                'type': 'pong',
                'timestamp': time.time()
            }
            await ws.send_json(response)
            
        else:
            logger.debug(f"Unknown WebSocket message type: {message_type}")

    async def broadcast_to_websockets(self, message_type: str, data: Dict[str, Any]):
        """Broadcast data to all connected WebSocket clients"""
        if not self.websockets:
            return 0

        message = {
            'type': message_type,
            'data': data,
            'timestamp': time.time(),
            'protocol': 'http'
        }

        disconnected = set()
        successful_sends = 0

        for ws in self.websockets:
            try:
                await ws.send_json(message)
                successful_sends += 1
            except Exception as e:
                logger.warning(f"Error sending to WebSocket, marking as disconnected: {e}")
                disconnected.add(ws)

        # Remove disconnected clients
        for ws in disconnected:
            self.websockets.remove(ws)
            logger.info(f"Removed disconnected WebSocket client. Total clients: {len(self.websockets)}")

        return successful_sends

    async def broadcast_system_status(self, status_data: Dict[str, Any]):
        """Broadcast system status via HTTP WebSockets"""
        try:
            successful_sends = await self.broadcast_to_websockets('system_status', status_data)
            logger.debug(f"Broadcast system status to {successful_sends} WebSocket clients")
            return successful_sends > 0
        except Exception as e:
            logger.error(f"Error broadcasting system status via HTTP: {e}")
            return False

    async def broadcast_sensor_data(self, sensor_data: Dict[str, Any]):
        """Broadcast sensor data via HTTP WebSockets"""
        try:
            successful_sends = await self.broadcast_to_websockets('sensor_data', sensor_data)
            if successful_sends > 0:
                logger.debug(f"Broadcast sensor data to {successful_sends} WebSocket clients")
            return successful_sends > 0
        except Exception as e:
            logger.error(f"Error broadcasting sensor data via HTTP: {e}")
            return False

    async def broadcast_alert(self, alert_data: Dict[str, Any]):
        """Broadcast alert via HTTP WebSockets"""
        try:
            successful_sends = await self.broadcast_to_websockets('alert', alert_data)
            logger.info(f"Broadcast alert to {successful_sends} WebSocket clients: {alert_data.get('message')}")
            return successful_sends > 0
        except Exception as e:
            logger.error(f"Error broadcasting alert via HTTP: {e}")
            return False

    async def handle_sensor_data(self, request):
        """Handle incoming sensor data via HTTP"""
        try:
            data = await request.json()

            # Validate required fields
            if not all(k in data for k in ['sensor_type', 'value', 'timestamp']):
                return web.Response(
                    text=json.dumps({"error": "Missing required fields: sensor_type, value, timestamp"}),
                    status=400,
                    content_type='application/json'
                )

            logger.info(f"HTTP sensor data received: {data.get('sensor_type')} = {data.get('value')}")

            # Process through handlers
            await self._call_handlers('sensor_data', data)

            return web.Response(
                text=json.dumps({
                    "status": "success",
                    "protocol": "http",
                    "message": "Sensor data processed",
                    "timestamp": time.time()
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
                    text=json.dumps({"error": "Missing required fields: message, severity, timestamp"}),
                    status=400,
                    content_type='application/json'
                )

            logger.info(f"HTTP alert received: {data.get('message')} (severity: {data.get('severity')})")

            await self._call_handlers('alerts', data)

            return web.Response(
                text=json.dumps({
                    "status": "success",
                    "protocol": "http",
                    "message": "Alert processed",
                    "timestamp": time.time()
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
                    "message": "Command processed",
                    "timestamp": time.time()
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
        try:
            status_data = {
                "status": "operational",
                "protocol": "http",
                "server": "running",
                "uptime": time.time() - self.start_time,
                "connected_clients": len(self.websockets),
                "timestamp": time.time()
            }
            return web.Response(
                text=json.dumps(status_data),
                content_type='application/json'
            )
        except Exception as e:
            logger.error(f"Error handling system status request: {e}")
            return web.Response(
                text=json.dumps({"error": "Internal server error"}),
                status=500,
                content_type='application/json'
            )

    async def handle_health(self, request):
        """Health check endpoint"""
        try:
            health_data = {
                "status": "healthy",
                "protocol": "http",
                "server": "running",
                "timestamp": time.time(),
                "connected_clients": len(self.websockets),
                "uptime_seconds": time.time() - self.start_time
            }
            return web.Response(
                text=json.dumps(health_data),
                content_type='application/json'
            )
        except Exception as e:
            logger.error(f"Error handling health check: {e}")
            return web.Response(
                text=json.dumps({"status": "unhealthy", "error": str(e)}),
                status=503,
                content_type='application/json'
            )

    async def _call_handlers(self, handler_type: str, data: Dict[str, Any]):
        """Call registered handlers for specific message type"""
        if handler_type in self.message_handlers:
            for handler in self.message_handlers[handler_type]:
                try:
                    await handler(data)
                except Exception as e:
                    logger.error(f"Error in HTTP handler for {handler_type}: {e}")

    def register_message_handler(self, handler_type: str, handler: Callable):
        """Register handler for specific message type"""
        if handler_type not in self.message_handlers:
            self.message_handlers[handler_type] = []
        self.message_handlers[handler_type].append(handler)
        logger.info(f"Registered HTTP handler for: {handler_type}")

    def get_server_info(self) -> Dict[str, Any]:
        """Get HTTP server information"""
        return {
            'port': settings.HTTP_PORT,
            'connected_clients': len(self.websockets),
            'uptime': time.time() - self.start_time,
            'active_handlers': {k: len(v) for k, v in self.message_handlers.items()}
        }

    async def shutdown(self):
        """Shutdown HTTP server gracefully"""
        try:
            logger.info("Shutting down HTTP server...")
            
            # Close all WebSocket connections
            if self.websockets:
                logger.info(f"Closing {len(self.websockets)} WebSocket connections")
                close_tasks = [ws.close() for ws in list(self.websockets)]
                await asyncio.gather(*close_tasks, return_exceptions=True)
                self.websockets.clear()

            # Shutdown server
            if self.site:
                await self.site.stop()
                logger.info("HTTP site stopped")
                
            if self.runner:
                await self.runner.cleanup()
                logger.info("HTTP runner cleaned up")
                
            logger.info("HTTP server shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during HTTP server shutdown: {e}")
