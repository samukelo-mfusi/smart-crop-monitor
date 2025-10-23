from datetime import datetime
from typing import List, Dict, Any
import logging
from sqlalchemy.orm import Session

from ..database.crud import create_alert
from ..core.config import settings

logger = logging.getLogger(__name__)


class AlertManager:
    """Manages alert generation and processing"""

    def __init__(self):
        self.alert_rules = {
            'soil': {
                'critical': {'min': settings.SOIL_MOISTURE_CRITICAL},
                'warning': {'min': settings.SOIL_MOISTURE_WARNING}
            },
            'temperature': {
                'critical': {'max': settings.TEMPERATURE_CRITICAL}
            }
        }

    def check_sensor_alerts(self, sensor_readings: List[Dict], db: Session, user_id: int) -> List[Dict]:
        """Check sensor readings and generate alerts if needed"""
        alerts = []

        for reading in sensor_readings:
            sensor_type = reading['sensor_type']
            zone = reading['zone']
            value = reading['value']

            if sensor_type in self.alert_rules:
                rules = self.alert_rules[sensor_type]

                for severity, thresholds in rules.items():
                    if self._check_thresholds(value, thresholds):
                        alert = self._create_alert(
                            sensor_type=sensor_type,
                            zone=zone,
                            value=value,
                            thresholds=thresholds,
                            severity=severity,
                            db=db,
                            user_id=user_id
                        )
                        if alert:
                            alerts.append(alert)

        return alerts

    def _check_thresholds(self, value: float, thresholds: Dict[str, float]) -> bool:
        """Check if value violates any thresholds"""
        if 'min' in thresholds and value < thresholds['min']:
            return True
        if 'max' in thresholds and value > thresholds['max']:
            return True
        return False

    def _create_alert(self, sensor_type: str, zone: str, value: float,
                      thresholds: Dict[str, float], severity: str,
                      db: Session, user_id: int) -> Dict:
        """Create an alert in the database"""
        try:
            # Generate alert message
            if 'min' in thresholds and value < thresholds['min']:
                reason = f"{sensor_type} in {zone} is critically low: {value:.1f}"
                recommendation = f"Increase {sensor_type} levels immediately"
                threshold_value = thresholds['min']
            else:
                reason = f"{sensor_type} in {zone} is critically high: {value:.1f}"
                recommendation = f"Reduce {sensor_type} levels immediately"
                threshold_value = thresholds['max']

            # Create alert in database
            alert_data = {
                'zone': zone,
                'sensor_type': sensor_type,
                'reason': reason,
                'severity': severity,
                'value': value,
                'threshold': threshold_value,
                'recommendation': recommendation,
                'acknowledged': False
            }

            db_alert = create_alert(db, alert_data, user_id)

            logger.info(f"Alert created: {reason}")

            return {
                'id': db_alert.id,
                'reason': reason,
                'severity': severity,
                'value': value,
                'recommendation': recommendation,
                'timestamp': db_alert.timestamp.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to create alert: {e}")
            return None

    def generate_system_alerts(self, system_metrics: Dict[str, Any],
                               db: Session, user_id: int) -> List[Dict]:
        """Generate system-level alerts"""
        alerts = []

        # Check system uptime
        if system_metrics.get('uptime', 100) < 90:
            alert_data = {
                'zone': 'system',
                'sensor_type': 'system',
                'reason': f"System uptime is low: {system_metrics['uptime']}%",
                'severity': 'warning',
                'value': system_metrics['uptime'],
                'threshold': 90,
                'recommendation': 'Check system connectivity and sensors',
                'acknowledged': False
            }
            db_alert = create_alert(db, alert_data, user_id)
            alerts.append({
                'id': db_alert.id,
                'reason': alert_data['reason'],
                'severity': 'warning',
                'timestamp': db_alert.timestamp.isoformat()
            })

        return alerts