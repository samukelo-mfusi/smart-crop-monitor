import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """Detects anomalies in sensor data using statistical methods"""

    def __init__(self):
        self.window_size = 10
        self.z_score_threshold = 2.5

    def detect_anomalies(self, sensor_readings: List[Dict]) -> List[Dict[str, Any]]:
        """Detect anomalies in sensor readings"""
        anomalies = []

        if len(sensor_readings) < self.window_size:
            return anomalies

        # Group by sensor type and zone
        readings_by_type = {}
        for reading in sensor_readings:
            key = f"{reading['sensor_type']}_{reading['zone']}"
            if key not in readings_by_type:
                readings_by_type[key] = []
            readings_by_type[key].append(reading)

        # Check each sensor group for anomalies
        for sensor_key, readings in readings_by_type.items():
            values = [r['value'] for r in readings]

            if len(values) >= self.window_size:
                recent_anomalies = self._check_z_score(values, readings)
                anomalies.extend(recent_anomalies)

        return anomalies

    def _check_z_score(self, values: List[float], readings: List[Dict]) -> List[Dict]:
        """Check for anomalies using Z-score method"""
        anomalies = []

        if len(values) < 2:
            return anomalies

        mean = np.mean(values[:-1])  # Mean of previous values
        std = np.std(values[:-1])  # Std of previous values

        if std == 0:  # Avoid division by zero
            return anomalies

        # Check the latest value
        latest_value = values[-1]
        z_score = abs(latest_value - mean) / std

        if z_score > self.z_score_threshold:
            latest_reading = readings[-1]
            anomaly = {
                'sensor_type': latest_reading['sensor_type'],
                'zone': latest_reading['zone'],
                'value': latest_value,
                'expected_range': (mean - 2 * std, mean + 2 * std),
                'z_score': z_score,
                'timestamp': datetime.utcnow(),
                'reason': f"Unusual {latest_reading['sensor_type']} reading detected"
            }
            anomalies.append(anomaly)

        return anomalies

    def check_threshold_violations(self, sensor_readings: List[Dict],
                                   thresholds: Dict[str, Dict]) -> List[Dict[str, Any]]:
        """Check for threshold violations"""
        violations = []

        for reading in sensor_readings:
            sensor_type = reading['sensor_type']
            zone = reading['zone']
            value = reading['value']

            if sensor_type in thresholds and zone in thresholds[sensor_type]:
                threshold_config = thresholds[sensor_type][zone]

                if 'min' in threshold_config and value < threshold_config['min']:
                    violations.append({
                        'sensor_type': sensor_type,
                        'zone': zone,
                        'value': value,
                        'threshold': threshold_config['min'],
                        'violation_type': 'below_min',
                        'timestamp': datetime.utcnow(),
                        'reason': f"{sensor_type} below minimum threshold in {zone}"
                    })

                if 'max' in threshold_config and value > threshold_config['max']:
                    violations.append({
                        'sensor_type': sensor_type,
                        'zone': zone,
                        'value': value,
                        'threshold': threshold_config['max'],
                        'violation_type': 'above_max',
                        'timestamp': datetime.utcnow(),
                        'reason': f"{sensor_type} above maximum threshold in {zone}"
                    })

        return violations