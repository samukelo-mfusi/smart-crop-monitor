# import asyncio
# import json
# import logging
# import time
# import uuid
# from typing import Dict, Any, Callable, Set, List
# from aiocoap import Context, Message, resource, error
# from aiocoap import numbers
# from ..core.config import settings

# logger = logging.getLogger(__name__)


# class CoAPObservationManager:
#     """Manages CoAP observers for real-time data updates"""

#     def __init__(self):
#         self.observers: Dict[str, Set[Any]] = {}
#         self.registered_clients: Dict[str, Dict] = {}

#     def add_observer(self, resource_path: str, observer):
#         if resource_path not in self.observers:
#             self.observers[resource_path] = set()
#         self.observers[resource_path].add(observer)

#     def remove_observer(self, resource_path: str, observer):
#         if resource_path in self.observers:
#             self.observers[resource_path].discard(observer)

#     def notify_observers(self, resource_path: str, data: Dict[str, Any]):
#         if resource_path in self.observers:
#             for observer in self.observers[resource_path].copy():
#                 try:
#                     observer.update(data)
#                 except Exception as e:
#                     logger.error(f"Error notifying observer: {e}")
#                     self.remove_observer(resource_path, observer)

#     def register_client(self, client_id: str, endpoint: str, resources: List[str]):
#         self.registered_clients[client_id] = {
#             'endpoint': endpoint,
#             'resources': resources,
#             'last_seen': time.time()
#         }

#     def get_active_clients(self) -> List[Dict]:
#         active_clients = []
#         for client_id, client_info in self.registered_clients.items():
#             if time.time() - client_info['last_seen'] < 3600:  # 1 hour timeout
#                 active_clients.append({**client_info, 'client_id': client_id})
#         return active_clients


# class CoAPSensorResource(resource.ObservableResource):
#     """CoAP resource for sensor data with observation support"""

#     def __init__(self, server):
#         super().__init__()
#         self.server = server
#         self.last_data = {}
#         self.data_history = []
#         self.max_history = 1000

#     async def render_post(self, request):
#         """Handle POST requests with sensor data"""
#         client_endpoint = request.remote.hostinfo if request.remote else "unknown"

#         try:
#             if not request.payload:
#                 return Message(code=4.00, payload=b"Empty payload")

#             payload = request.payload.decode('utf-8')
#             data = json.loads(payload)

#             required_fields = ['sensor_type', 'value', 'timestamp', 'device_id']
#             if not all(k in data for k in required_fields):
#                 return Message(
#                     code=4.00,
#                     payload=json.dumps({
#                         "error": "Missing required fields",
#                         "required": required_fields
#                     }).encode('utf-8')
#                 )

#             # Validate data types and ranges
#             if not self._validate_sensor_data(data):
#                 return Message(code=4.00, payload=b"Invalid sensor data")

#             logger.info(
#                 f"CoAP sensor data from {data['device_id']} at {client_endpoint}: {data['sensor_type']} = {data['value']}")

#             # Store data
#             sensor_key = f"{data['device_id']}_{data['sensor_type']}"
#             self.last_data[sensor_key] = data
#             self.data_history.append(data)

#             # Keep history manageable
#             if len(self.data_history) > self.max_history:
#                 self.data_history = self.data_history[-self.max_history:]

#             # Notify observers
#             self.updated_state()
#             self.server.observation_manager.notify_observers('sensors/data', data)

#             # Process through handlers
#             await self.server._call_handlers('sensor_data', data)

#             response_payload = json.dumps({
#                 "status": "success",
#                 "protocol": "coap",
#                 "message": "Sensor data processed",
#                 "timestamp": time.time(),
#                 "message_id": str(uuid.uuid4())
#             }).encode('utf-8')

#             return Message(
#                 code=2.04,
#                 payload=response_payload,
#                 content_format=numbers.media_types_rev['application/json']
#             )

#         except json.JSONDecodeError:
#             return Message(code=4.00, payload=b"Invalid JSON")
#         except Exception as e:
#             logger.error(f"CoAP sensor data error from {client_endpoint}: {e}")
#             return Message(code=5.00, payload=b"Internal server error")

#     async def render_get(self, request):
#         """Handle GET requests for current sensor data"""
#         device_filter = request.opt.uri_query
#         device_id = None

#         if device_filter:
#             for query in device_filter:
#                 if query.startswith('device_id='):
#                     device_id = query.split('=')[1]
#                     break

#         if device_id:
#             # Return data for specific device
#             device_data = {k: v for k, v in self.last_data.items() if k.startswith(device_id)}
#             response_data = {
#                 "device_id": device_id,
#                 "sensors": list(device_data.values()),
#                 "timestamp": time.time()
#             }
#         else:
#             # Return all recent data
#             response_data = {
#                 "sensors": list(self.last_data.values()),
#                 "timestamp": time.time(),
#                 "total_sensors": len(self.last_data)
#             }

#         return Message(
#             payload=json.dumps(response_data).encode('utf-8'),
#             content_format=numbers.media_types_rev['application/json']
#         )

#     def _validate_sensor_data(self, data: Dict[str, Any]) -> bool:
#         """Validate sensor data ranges and types"""
#         try:
#             sensor_type = data['sensor_type']
#             value = float(data['value'])

#             validation_rules = {
#                 'soil_moisture': (0, 100),
#                 'temperature': (-50, 100),
#                 'humidity': (0, 100),
#                 'light': (0, 100000),
#                 'ph': (0, 14)
#             }

#             if sensor_type in validation_rules:
#                 min_val, max_val = validation_rules[sensor_type]
#                 return min_val <= value <= max_val

#             return True  # Unknown sensor type, accept anyway

#         except (ValueError, KeyError):
#             return False


# class CoAPAlertResource(resource.Resource):
#     """CoAP resource for handling alerts"""

#     def __init__(self, server):
#         super().__init__()
#         self.server = server
#         self.active_alerts = {}

#     async def render_post(self, request):
#         """Handle POST requests with alerts"""
#         client_endpoint = request.remote.hostinfo if request.remote else "unknown"

#         try:
#             if not request.payload:
#                 return Message(code=4.00, payload=b"Empty payload")

#             payload = request.payload.decode('utf-8')
#             data = json.loads(payload)

#             required_fields = ['message', 'severity', 'timestamp', 'alert_id', 'device_id']
#             if not all(k in data for k in required_fields):
#                 return Message(code=4.00, payload=b"Missing required fields")

#             # Validate severity
#             if data['severity'] not in ['low', 'medium', 'high', 'critical']:
#                 return Message(code=4.00, payload=b"Invalid severity level")

#             logger.warning(
#                 f"CoAP alert from {data['device_id']} at {client_endpoint}: {data['alert_id']} - {data['message']}")

#             # Store active alert
#             self.active_alerts[data['alert_id']] = {
#                 **data,
#                 'received_at': time.time(),
#                 'source_endpoint': client_endpoint
#             }

#             # Process through handlers
#             await self.server._call_handlers('alerts', data)

#             # Broadcast to all registered clients for critical alerts
#             if data['severity'] in ['high', 'critical']:
#                 await self.server._broadcast_critical_alert(data)

#             response_payload = json.dumps({
#                 "status": "success",
#                 "protocol": "coap",
#                 "message": "Alert processed",
#                 "timestamp": time.time(),
#                 "alert_id": data['alert_id']
#             }).encode('utf-8')

#             return Message(
#                 code=2.04,
#                 payload=response_payload,
#                 content_format=numbers.media_types_rev['application/json']
#             )

#         except Exception as e:
#             logger.error(f"CoAP alert error from {client_endpoint}: {e}")
#             return Message(code=5.00, payload=b"Internal server error")

#     async def render_get(self, request):
#         """Handle GET requests for active alerts"""
#         alert_filter = request.opt.uri_query
#         severity_filter = None

#         if alert_filter:
#             for query in alert_filter:
#                 if query.startswith('severity='):
#                     severity_filter = query.split('=')[1]
#                     break

#         if severity_filter:
#             filtered_alerts = {k: v for k, v in self.active_alerts.items()
#                                if v['severity'] == severity_filter}
#         else:
#             filtered_alerts = self.active_alerts

#         response_data = {
#             "alerts": list(filtered_alerts.values()),
#             "total_alerts": len(filtered_alerts),
#             "timestamp": time.time()
#         }

#         return Message(
#             payload=json.dumps(response_data).encode('utf-8'),
#             content_format=numbers.media_types_rev['application/json']
#         )


# class CoAPCommandResource(resource.Resource):
#     """CoAP resource for handling commands"""

#     def __init__(self, server):
#         super().__init__()
#         self.server = server
#         self.command_history = []
#         self.max_history = 500

#     async def render_post(self, request):
#         """Handle POST requests with commands"""
#         client_endpoint = request.remote.hostinfo if request.remote else "unknown"

#         try:
#             if not request.payload:
#                 return Message(code=4.00, payload=b"Empty payload")

#             payload = request.payload.decode('utf-8')
#             data = json.loads(payload)

#             required_fields = ['command', 'timestamp', 'requester_id']
#             if not all(k in data for k in required_fields):
#                 return Message(code=4.00, payload=b"Missing required fields")

#             # Validate command
#             valid_commands = ['irrigation_start', 'irrigation_stop', 'sensor_read',
#                               'system_status', 'device_restart', 'config_update']
#             if data['command'] not in valid_commands:
#                 return Message(code=4.00, payload=b"Invalid command")

#             logger.info(f"CoAP command from {data['requester_id']} at {client_endpoint}: {data['command']}")

#             # Store command in history
#             command_record = {
#                 **data,
#                 'received_at': time.time(),
#                 'command_id': str(uuid.uuid4()),
#                 'source_endpoint': client_endpoint,
#                 'status': 'received'
#             }
#             self.command_history.append(command_record)

#             # Keep history manageable
#             if len(self.command_history) > self.max_history:
#                 self.command_history = self.command_history[-self.max_history:]

#             # Process through handlers
#             await self.server._call_handlers('commands', data)

#             response_payload = json.dumps({
#                 "status": "success",
#                 "protocol": "coap",
#                 "message": "Command executed",
#                 "timestamp": time.time(),
#                 "command_id": command_record['command_id']
#             }).encode('utf-8')

#             return Message(
#                 code=2.04,
#                 payload=response_payload,
#                 content_format=numbers.media_types_rev['application/json']
#             )

#         except Exception as e:
#             logger.error(f"CoAP command error from {client_endpoint}: {e}")
#             return Message(code=5.00, payload=b"Internal server error")

#     async def render_get(self, request):
#         """Handle GET requests for command history"""
#         limit = 50
#         limit_filter = request.opt.uri_query

#         if limit_filter:
#             for query in limit_filter:
#                 if query.startswith('limit='):
#                     try:
#                         limit = min(int(query.split('=')[1]), 200)  # Max 200 records
#                     except ValueError:
#                         pass

#         recent_commands = self.command_history[-limit:] if self.command_history else []

#         response_data = {
#             "commands": recent_commands,
#             "total_commands": len(self.command_history),
#             "timestamp": time.time()
#         }

#         return Message(
#             payload=json.dumps(response_data).encode('utf-8'),
#             content_format=numbers.media_types_rev['application/json']
#         )


# class CoAPDeviceRegistry(resource.Resource):
#     """CoAP resource for device registration and management"""

#     def __init__(self, server):
#         super().__init__()
#         self.server = server

#     async def render_post(self, request):
#         """Handle device registration"""
#         client_endpoint = request.remote.hostinfo if request.remote else "unknown"

#         try:
#             if not request.payload:
#                 return Message(code=4.00, payload=b"Empty payload")

#             payload = request.payload.decode('utf-8')
#             data = json.loads(payload)

#             required_fields = ['device_id', 'device_type', 'capabilities', 'timestamp']
#             if not all(k in data for k in required_fields):
#                 return Message(code=4.00, payload=b"Missing required fields")

#             logger.info(f"CoAP device registration: {data['device_id']} from {client_endpoint}")

#             # Register device with observation manager
#             self.server.observation_manager.register_client(
#                 data['device_id'],
#                 client_endpoint,
#                 data.get('resources', [])
#             )

#             response_payload = json.dumps({
#                 "status": "registered",
#                 "protocol": "coap",
#                 "device_id": data['device_id'],
#                 "assigned_resources": ["sensors/data", "alerts", "commands"],
#                 "registration_time": time.time(),
#                 "server_endpoints": {
#                     "sensors": f"coap://{settings.COAP_HOST}:{settings.COAP_PORT}/sensors/data",
#                     "alerts": f"coap://{settings.COAP_HOST}:{settings.COAP_PORT}/alerts",
#                     "commands": f"coap://{settings.COAP_HOST}:{settings.COAP_PORT}/commands"
#                 }
#             }).encode('utf-8')

#             return Message(
#                 code=2.01,  # Created
#                 payload=response_payload,
#                 content_format=numbers.media_types_rev['application/json']
#             )

#         except Exception as e:
#             logger.error(f"CoAP device registration error from {client_endpoint}: {e}")
#             return Message(code=5.00, payload=b"Internal server error")


# class CoAPHealthResource(resource.Resource):
#     """CoAP resource for health checks"""

#     def __init__(self, server):
#         super().__init__()
#         self.server = server

#     async def render_get(self, request):
#         """Handle GET requests for health checks"""
#         health_data = {
#             "status": "healthy",
#             "protocol": "coap",
#             "server": "running",
#             "timestamp": time.time(),
#             "start_time": self.server.start_time,
#             "uptime_seconds": time.time() - self.server.start_time,
#             "active_handlers": len(self.server.message_handlers),
#             "messages_processed": self.server.metrics['messages_received'],
#             "active_clients": len(self.server.observation_manager.get_active_clients())
#         }

#         return Message(
#             payload=json.dumps(health_data).encode('utf-8'),
#             content_format=numbers.media_types_rev['application/json']
#         )


# class CoAPServer:
#     def __init__(self):
#         self.context = None
#         self.is_running = False
#         self.message_handlers = {}
#         self.observation_manager = CoAPObservationManager()
#         self.start_time = time.time()
#         self.metrics = {
#             'messages_received': 0,
#             'messages_sent': 0,
#             'errors': 0,
#             'last_client_activity': time.time()
#         }
#         self.registered_endpoints = set()

#     async def start_server(self):
#         """Start CoAP production server"""
#         try:
#             # Create resource tree
#             root = resource.Site()

#             # Add all resources
#             root.add_resource(['sensors', 'data'], CoAPSensorResource(self))
#             root.add_resource(['alerts'], CoAPAlertResource(self))
#             root.add_resource(['commands'], CoAPCommandResource(self))
#             root.add_resource(['devices', 'register'], CoAPDeviceRegistry(self))
#             root.add_resource(['health'], CoAPHealthResource(self))
#             root.add_resource(['.well-known', 'core'], resource.WKCResource(root.get_resources_as_linkheader))

#             self.context = await Context.create_server_context(
#                 root,
#                 bind=(settings.COAP_HOST, settings.COAP_PORT)
#             )

#             self.is_running = True
#             self.start_time = time.time()

#             logger.info(f"CoAP Server running on coap://{settings.COAP_HOST}:{settings.COAP_PORT}")

#             # Start maintenance tasks
#             asyncio.create_task(self._cleanup_expired_data())
#             asyncio.create_task(self._monitor_client_activity())

#             return True

#         except Exception as e:
#             logger.error(f"CoAP server startup failed: {e}")
#             return False

#     async def _cleanup_expired_data(self):
#         """Clean up expired data and inactive clients"""
#         while self.is_running:
#             try:
#                 await asyncio.sleep(300)  # Run every 5 minutes

#                 # Clean up old alerts (older than 24 hours)
#                 current_time = time.time()
#                 expired_alerts = [
#                     alert_id for alert_id, alert in self.active_alerts.items()
#                     if current_time - alert.get('received_at', 0) > 86400
#                 ]
#                 for alert_id in expired_alerts:
#                     del self.active_alerts[alert_id]

#                 logger.debug("CoAP data cleanup completed")

#             except Exception as e:
#                 logger.error(f"CoAP cleanup error: {e}")

#     async def _monitor_client_activity(self):
#         """Monitor client activity and log statistics"""
#         while self.is_running:
#             try:
#                 await asyncio.sleep(60)  # Run every minute

#                 active_clients = self.observation_manager.get_active_clients()
#                 if active_clients:
#                     logger.info(f"CoAP active clients: {len(active_clients)}")

#             except Exception as e:
#                 logger.error(f"CoAP client monitoring error: {e}")

#     async def publish_sensor_data(self, sensor_data: Dict[str, Any]):
#         """Publish sensor data to CoAP observers"""
#         if not self.is_running:
#             return False

#         try:
#             self.observation_manager.notify_observers('sensors/data', sensor_data)
#             self.metrics['messages_sent'] += 1
#             return True

#         except Exception as e:
#             logger.error(f"CoAP publish error: {e}")
#             self.metrics['errors'] += 1
#             return False

#     async def publish_alert(self, alert_data: Dict[str, Any]):
#         """Publish alert to registered CoAP clients"""
#         if not self.is_running:
#             return False

#         try:
#             # Send to all registered clients for critical alerts
#             if alert_data.get('severity') in ['high', 'critical']:
#                 await self._broadcast_critical_alert(alert_data)

#             self.metrics['messages_sent'] += 1
#             return True

#         except Exception as e:
#             logger.error(f"CoAP alert publish error: {e}")
#             self.metrics['errors'] += 1
#             return False

#     async def _broadcast_critical_alert(self, alert_data: Dict[str, Any]):
#         """Broadcast critical alert to all registered clients"""
#         active_clients = self.observation_manager.get_active_clients()

#         for client in active_clients:
#             try:
#                 success = await self.send_coap_message(
#                     client['endpoint'] + '/alerts',
#                     alert_data,
#                     confirmable=True
#                 )
#                 if success:
#                     logger.info(f"Critical alert sent to {client['client_id']}")
#             except Exception as e:
#                 logger.error(f"Failed to send alert to {client['client_id']}: {e}")

#     async def _call_handlers(self, handler_type: str, data: Dict[str, Any]):
#         """Call registered message handlers"""
#         self.metrics['messages_received'] += 1
#         self.metrics['last_client_activity'] = time.time()

#         if handler_type in self.message_handlers:
#             for handler in self.message_handlers[handler_type]:
#                 try:
#                     await handler(data)
#                 except Exception as e:
#                     logger.error(f"CoAP handler error: {e}")
#                     self.metrics['errors'] += 1

#     def register_message_handler(self, handler_type: str, handler: Callable):
#         """Register message handler"""
#         if handler_type not in self.message_handlers:
#             self.message_handlers[handler_type] = []
#         self.message_handlers[handler_type].append(handler)

#     async def send_coap_message(self, target_uri: str, data: Dict[str, Any], confirmable: bool = True) -> bool:
#         """Send CoAP message to target URI"""
#         try:
#             if not self.context:
#                 return False

#             payload = json.dumps(data).encode('utf-8')
#             message = Message(
#                 code=1,  # POST
#                 payload=payload,
#                 uri=target_uri,
#                 content_format=numbers.media_types_rev['application/json']
#             )

#             if not confirmable:
#                 message.type = 1  # NON

#             request = self.context.request(message)
#             request.timeout = 10

#             try:
#                 response = await request.response
#                 return response.code.is_successful()
#             except error.RequestTimedOut:
#                 logger.warning(f"CoAP request timeout to {target_uri}")
#                 return False

#         except Exception as e:
#             logger.error(f"CoAP send error to {target_uri}: {e}")
#             return False

#     async def shutdown(self):
#         """Shutdown CoAP server"""
#         try:
#             self.is_running = False

#             if self.context:
#                 await self.context.shutdown()

#             logger.info("CoAP server shutdown complete")

#         except Exception as e:
#             logger.error(f"CoAP shutdown error: {e}")
