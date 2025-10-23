import asyncio
import logging
from datetime import datetime, timedelta
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class RealTimeService:
    """Service for handling real-time data updates"""

    def __init__(self, api_client, update_interval: int = 300):
        self.api_client = api_client
        self.update_interval = update_interval
        self.is_running = False
        self.callbacks = []
        self.last_update = None

    def add_callback(self, callback: Callable):
        """Add callback function to be called on data updates"""
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """Remove callback function"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def start(self):
        """Start the real-time update service"""
        self.is_running = True
        logger.info("Real-time service started")

        while self.is_running:
            try:
                await self._fetch_and_update()
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error(f"Error in real-time service: {e}")
                await asyncio.sleep(60)  # Wait before retrying

    async def _fetch_and_update(self):
        """Fetch new data and trigger callbacks"""
        try:
            # Get latest dashboard data
            dashboard_data = self.api_client.get_dashboard_data()

            if dashboard_data:
                self.last_update = datetime.now()

                # Notify all callbacks
                for callback in self.callbacks:
                    try:
                        callback(dashboard_data)
                    except Exception as e:
                        logger.error(f"Error in callback: {e}")

                logger.debug("Real-time data updated successfully")
            else:
                logger.warning("Failed to fetch dashboard data")

        except Exception as e:
            logger.error(f"Error fetching data: {e}")

    def stop(self):
        """Stop the real-time service"""
        self.is_running = False
        logger.info("Real-time service stopped")

    def get_status(self) -> dict:
        """Get service status"""
        return {
            "running": self.is_running,
            "last_update": self.last_update.isoformat() if self.last_update else None,
            "update_interval": self.update_interval,
            "callbacks_count": len(self.callbacks)
        }

    def manual_refresh(self):
        """Trigger manual data refresh"""
        asyncio.create_task(self._fetch_and_update())