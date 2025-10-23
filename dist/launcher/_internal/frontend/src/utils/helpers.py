from datetime import datetime, timedelta
import re
from typing import Any, Dict


def format_timestamp(timestamp_str: str) -> str:
    """Format timestamp for display"""
    try:
        if 'T' in timestamp_str:
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(timestamp_str)

        now = datetime.now()
        diff = now - dt

        if diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            return f"{diff.seconds // 3600}h ago"
        elif diff.seconds > 60:
            return f"{diff.seconds // 60}m ago"
        else:
            return "Just now"
    except:
        return timestamp_str


def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None


def validate_password_strength(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"

    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one number"

    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(char.islower() for char in password):
        return False, "Password must contain at least one lowercase letter"

    return True, "Password is strong"


def calculate_water_savings(historical_data: list) -> float:
    """Calculate estimated water savings"""
    if not historical_data:
        return 0.0

    total_water_need = sum(day.get('water_need', 0) for day in historical_data)
    optimal_water_need = len(historical_data) * 10  # Assume 10L per day optimal

    if optimal_water_need == 0:
        return 0.0

    savings = max(0, (optimal_water_need - total_water_need) / optimal_water_need * 100)
    return min(savings, 100)  # Cap at 100%


def get_system_health_score(metrics: Dict[str, Any]) -> int:
    """Calculate overall system health score"""
    score = 0
    total_weights = 0

    # Uptime weight: 40%
    uptime = metrics.get('uptime', 0)
    score += uptime * 0.4
    total_weights += 0.4

    # Data quality weight: 30%
    data_points = metrics.get('data_points_today', 0)
    data_quality = min(100, data_points / 48 * 100)  # 48 = 2 zones * 4 sensors * 6 readings/hour
    score += data_quality * 0.3
    total_weights += 0.3

    # Zone coverage weight: 30%
    zones_active = metrics.get('zones_active', 0)
    coverage = (zones_active / 2) * 100  # 2 total zones
    score += coverage * 0.3
    total_weights += 0.3

    return int(score / total_weights)


def format_water_volume(liters: float) -> str:
    """Format water volume for display"""
    if liters < 1:
        return f"{liters * 1000:.0f}ml"
    elif liters < 1000:
        return f"{liters:.1f}L"
    else:
        return f"{liters / 1000:.1f}kL"


def get_severity_color(severity: str) -> str:
    """Get color for alert severity"""
    colors = {
        'critical': '#e74c3c',
        'warning': '#f39c12',
        'info': '#3498db',
        'success': '#27ae60'
    }
    return colors.get(severity.lower(), '#95a5a6')


def is_data_stale(last_update: str, threshold_minutes: int = 10) -> bool:
    """Check if data is stale"""
    try:
        if 'T' in last_update:
            last_dt = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
        else:
            last_dt = datetime.fromisoformat(last_update)

        return (datetime.now() - last_dt) > timedelta(minutes=threshold_minutes)
    except:
        return True


def deep_merge(dict1: Dict, dict2: Dict) -> Dict:
    """Deep merge two dictionaries"""
    result = dict1.copy()

    for key, value in dict2.items():
        if (key in result and isinstance(result[key], dict)
                and isinstance(value, dict)):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result