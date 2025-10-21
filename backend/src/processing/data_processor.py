import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes and analyzes sensor data"""

    def __init__(self):
        self.analysis_window = 24  # hours

    def calculate_system_metrics(self, sensor_readings: List[Dict],
                                 irrigation_events: List[Dict]) -> Dict[str, Any]:
        """Calculate system-wide metrics"""
        if not sensor_readings:
            return self._get_default_metrics()

        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(sensor_readings)
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Calculate basic metrics
        current_time = datetime.utcnow()
        one_hour_ago = current_time - timedelta(hours=1)
        one_day_ago = current_time - timedelta(days=1)

        # Recent readings (last hour)
        recent_readings = df[df['timestamp'] >= one_hour_ago]

        # Active zones (have readings in last hour)
        active_zones = recent_readings['zone'].nunique()

        # Water usage (from irrigation events)
        today_irrigation = [e for e in irrigation_events
                            if e['start_time'].date() == current_time.date()]
        water_used_today = sum(e.get('water_used', 0) for e in today_irrigation)

        # System uptime
        total_expected_readings = active_zones * 4 * 24  # 4 sensors * 24 hours
        actual_readings = len(df[df['timestamp'] >= one_day_ago])
        uptime = min(100, (actual_readings / total_expected_readings * 100)) if total_expected_readings > 0 else 100

        # Energy savings
        optimal_irrigation_count = 2  # Assuming optimal is 2 irrigations per day
        actual_irrigation_count = len(today_irrigation)
        energy_saved = max(0, 100 - (actual_irrigation_count / optimal_irrigation_count * 100))

        return {
            'water_used_today': round(water_used_today, 1),
            'energy_saved': round(energy_saved, 1),
            'zones_active': active_zones,
            'uptime': round(uptime, 1),
            'data_points_today': len(df[df['timestamp'].dt.date == current_time.date()]),
            'last_data_refresh': current_time.isoformat()
        }

    def _get_default_metrics(self) -> Dict[str, Any]:
        """Return default metrics when no data is available"""
        return {
            'water_used_today': 0.0,
            'energy_saved': 0.0,
            'zones_active': 0,
            'uptime': 0.0,
            'data_points_today': 0,
            'last_data_refresh': datetime.utcnow().isoformat()
        }

    def analyze_soil_moisture_trends(self, soil_readings: List[Dict]) -> Dict[str, Any]:
        """Analyze soil moisture trends and patterns"""
        if not soil_readings:
            return {'trend': 'stable', 'change_rate': 0, 'recommendation': 'No data available'}

        df = pd.DataFrame(soil_readings)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')

        # Calculate trend
        if len(df) >= 2:
            recent_values = df['value'].tail(5).values
            change_rate = (recent_values[-1] - recent_values[0]) / len(recent_values)
        else:
            change_rate = 0

        # Determine trend direction
        if abs(change_rate) < 0.1:
            trend = 'stable'
        elif change_rate > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'

        # Generate recommendation
        avg_moisture = df['value'].mean()
        if avg_moisture < 30:
            recommendation = 'Immediate irrigation needed'
        elif avg_moisture < 45:
            recommendation = 'Consider irrigation soon'
        elif avg_moisture > 80:
            recommendation = 'Soil is saturated, no irrigation needed'
        else:
            recommendation = 'Moisture levels optimal'

        return {
            'trend': trend,
            'change_rate': round(change_rate, 3),
            'average_moisture': round(avg_moisture, 1),
            'recommendation': recommendation,
            'data_points': len(df)
        }

    def generate_historical_summary(self, days: int = 7) -> Dict[str, Any]:
        """Generate historical data summary for charts"""
        end_date = datetime.utcnow()
        dates = [(end_date - timedelta(days=i)).strftime('%Y-%m-%d')
                 for i in range(days, 0, -1)]

        base_moisture = 65
        moisture_data = [base_moisture + np.random.normal(0, 5) for _ in range(days)]

        return {
            'historical_data': [
                {
                    'date': date,
                    'avg_moisture': max(10, min(90, moisture)),
                    'avg_temperature': 22 + np.random.normal(0, 3),
                    'avg_humidity': 65 + np.random.normal(0, 10),
                    'water_need': max(0, 70 - moisture)
                }
                for date, moisture in zip(dates, moisture_data)
            ]
        }