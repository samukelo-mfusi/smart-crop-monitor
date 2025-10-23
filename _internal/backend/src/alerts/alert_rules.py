from typing import Dict, Any


class AlertRules:
    """Defines rules for generating alerts"""

    @staticmethod
    def get_sensor_rules() -> Dict[str, Dict]:
        return {
            'soil': {
                'critical': {'min': 30.0},
                'warning': {'min': 40.0}
            },
            'temperature': {
                'critical': {'max': 35.0},
                'warning': {'max': 32.0}
            },
            'humidity': {
                'critical': {'min': 20.0, 'max': 90.0},
                'warning': {'min': 30.0, 'max': 80.0}
            }
        }

    @staticmethod
    def get_system_rules() -> Dict[str, Dict]:
        return {
            'uptime': {'warning': {'min': 90.0}},
            'data_freshness': {'warning': {'max': 300}},  # 5 minutes in seconds
            'sensor_health': {'critical': {'min': 0.5}}  # At least 50% sensors reporting
        }

    @staticmethod
    def get_irrigation_rules() -> Dict[str, Dict]:
        return {
            'water_usage': {
                'warning': {'max': 50.0},  # liters per day
                'critical': {'max': 100.0}
            },
            'irrigation_frequency': {
                'warning': {'max': 5},  # times per day
                'critical': {'max': 10}
            }
        }