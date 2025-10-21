from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from .models import User, SensorReading, Alert, SystemSetting, IrrigationEvent
from ..core.security import get_password_hash

logger = logging.getLogger(__name__)


# User operations
def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, username: str, email: str, full_name: str, password: str) -> User:
    hashed_password = get_password_hash(password)
    db_user = User(
        username=username,
        email=email,
        full_name=full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def update_user_password(db: Session, user_id: int, new_password: str) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.hashed_password = get_password_hash(new_password)
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user


def update_user_profile(db: Session, user_id: int, full_name: str = None, email: str = None) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user:
        if full_name:
            user.full_name = full_name
        if email:
            user.email = email
        user.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(user)
    return user


# Sensor reading operations
def create_sensor_reading(db: Session, reading_data: dict, user_id: int) -> SensorReading:
    valid_fields = {
        'sensor_type', 'value', 'zone', 'timestamp', 'unit', 'source',
        'device_id', 'latitude', 'longitude'
    }

    filtered_data = {k: v for k, v in reading_data.items() if k in valid_fields}
    db_reading = SensorReading(**filtered_data, user_id=user_id)
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


def get_latest_sensor_readings(db: Session, user_id: int, hours: int = 24) -> List[SensorReading]:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    return db.query(SensorReading).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.timestamp >= cutoff_time
        )
    ).order_by(desc(SensorReading.timestamp)).all()


def get_sensor_readings_by_zone_type(db: Session, user_id: int, zone: str, sensor_type: str,
                                     hours: int = 24) -> List[SensorReading]:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    return db.query(SensorReading).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.zone == zone,
            SensorReading.sensor_type == sensor_type,
            SensorReading.timestamp >= cutoff_time
        )
    ).order_by(SensorReading.timestamp).all()


def get_sensor_readings_by_device(db: Session, user_id: int, device_id: str, hours: int = 24) -> List[SensorReading]:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    return db.query(SensorReading).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.device_id == device_id,
            SensorReading.timestamp >= cutoff_time
        )
    ).order_by(desc(SensorReading.timestamp)).all()


def get_active_devices(db: Session, user_id: int, hours: int = 24) -> List[str]:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    result = db.query(SensorReading.device_id).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.device_id.isnot(None),
            SensorReading.timestamp >= cutoff_time
        )
    ).distinct().all()

    return [r.device_id for r in result if r.device_id]


# Alert operations
def create_alert(db: Session, alert_data: dict, user_id: int) -> Alert:
    valid_fields = {
        'reason', 'severity', 'value', 'threshold', 'recommendation',
        'zone', 'sensor_type', 'device_id', 'timestamp'
    }

    filtered_data = {k: v for k, v in alert_data.items() if k in valid_fields}
    db_alert = Alert(**filtered_data, user_id=user_id)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


def get_alerts(db: Session, user_id: int, acknowledged: bool = None,
               hours: int = 24) -> List[Alert]:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    query = db.query(Alert).filter(
        and_(
            Alert.user_id == user_id,
            Alert.timestamp >= cutoff_time
        )
    )

    if acknowledged is not None:
        query = query.filter(Alert.acknowledged == acknowledged)

    return query.order_by(desc(Alert.timestamp)).all()


def acknowledge_alert(db: Session, alert_id: int, user_id: int) -> Optional[Alert]:
    alert = db.query(Alert).filter(
        and_(
            Alert.id == alert_id,
            Alert.user_id == user_id
        )
    ).first()

    if alert:
        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        db.commit()
        db.refresh(alert)

    return alert


def get_unacknowledged_alerts_count(db: Session, user_id: int, hours: int = 24) -> int:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    return db.query(Alert).filter(
        and_(
            Alert.user_id == user_id,
            Alert.acknowledged == False,
            Alert.timestamp >= cutoff_time
        )
    ).count()


# System settings operations
def get_system_setting(db: Session, key: str) -> Optional[SystemSetting]:
    return db.query(SystemSetting).filter(SystemSetting.key == key).first()


def create_or_update_setting(db: Session, key: str, value: str, description: str = None) -> SystemSetting:
    setting = get_system_setting(db, key)

    if setting:
        setting.value = value
        if description:
            setting.description = description
        setting.updated_at = datetime.utcnow()
    else:
        setting = SystemSetting(key=key, value=value, description=description)
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting

def get_all_users(db: Session) -> List[Any]:
    """Get all users from database"""
    from .models import User
    return db.query(User).all()

def get_all_settings(db: Session) -> list[type[SystemSetting]]:
    return db.query(SystemSetting).all()


def get_water_usage_stats(db: Session, user_id: int) -> dict:
    try:
        today = datetime.utcnow().date()
        today_start = datetime(today.year, today.month, today.day)

        today_usage = db.query(func.sum(IrrigationEvent.water_used)).filter(
            IrrigationEvent.user_id == user_id,
            IrrigationEvent.start_time >= today_start
        ).scalar() or 0.0

        week_ago = datetime.utcnow() - timedelta(days=7)
        weekly_usage = db.query(func.sum(IrrigationEvent.water_used)).filter(
            IrrigationEvent.user_id == user_id,
            IrrigationEvent.start_time >= week_ago
        ).scalar() or 0.0

        total_events = db.query(func.count(IrrigationEvent.id)).filter(
            IrrigationEvent.user_id == user_id
        ).scalar() or 0

        return {
            "today_water_used": round(today_usage, 2),
            "weekly_water_used": round(weekly_usage, 2),
            "total_irrigation_events": total_events,
            "last_updated": datetime.utcnow()
        }

    except Exception as e:
        logger.error(f"Error getting water usage stats: {e}")
        return {
            "today_water_used": 0.0,
            "weekly_water_used": 0.0,
            "total_irrigation_events": 0,
            "last_updated": datetime.utcnow()
        }


# Irrigation operations
def create_irrigation_event(db: Session, zone: str, duration: int, user_id: int) -> IrrigationEvent:
    zone_flow_rates = {
        "field_1": 2.5,
        "field_2": 2.0,
        "zone1": 2.5,
        "zone2": 2.0,
        "zone_1": 2.5,
        "zone_2": 2.0
    }

    flow_rate = zone_flow_rates.get(zone, 2.0)
    water_used = duration * flow_rate

    db_event = IrrigationEvent(
        zone=zone,
        duration=duration,
        water_used=water_used,
        user_id=user_id,
        start_time=datetime.utcnow(),
        status="completed"
    )
    db.add(db_event)
    db.commit()
    db.refresh(db_event)

    logger.info(f"Created irrigation event: {zone}, {duration}min, {water_used}L water")
    return db_event


def get_recent_irrigation_events(db: Session, user_id: int, days: int = 7) -> List[IrrigationEvent]:
    cutoff_time = datetime.utcnow() - timedelta(days=days)
    return db.query(IrrigationEvent).filter(
        and_(
            IrrigationEvent.user_id == user_id,
            IrrigationEvent.start_time >= cutoff_time
        )
    ).order_by(desc(IrrigationEvent.start_time)).all()


def get_irrigation_stats(db: Session, user_id: int, days: int = 30) -> dict:
    cutoff_time = datetime.utcnow() - timedelta(days=days)

    total_water = db.query(func.sum(IrrigationEvent.water_used)).filter(
        and_(
            IrrigationEvent.user_id == user_id,
            IrrigationEvent.start_time >= cutoff_time
        )
    ).scalar() or 0.0

    total_events = db.query(func.count(IrrigationEvent.id)).filter(
        and_(
            IrrigationEvent.user_id == user_id,
            IrrigationEvent.start_time >= cutoff_time
        )
    ).scalar() or 0

    avg_duration = db.query(func.avg(IrrigationEvent.duration)).filter(
        and_(
            IrrigationEvent.user_id == user_id,
            IrrigationEvent.start_time >= cutoff_time
        )
    ).scalar() or 0

    return {
        "total_water_used": round(total_water, 2),
        "total_events": total_events,
        "average_duration": round(avg_duration, 1),
        "period_days": days
    }


# Analytics operations
def get_daily_averages(db: Session, user_id: int, days: int = 7) -> List[dict]:
    cutoff_time = datetime.utcnow() - timedelta(days=days)

    result = db.query(
        func.date(SensorReading.timestamp).label('date'),
        func.avg(SensorReading.value).label('avg_moisture'),
        func.count(SensorReading.id).label('reading_count')
    ).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.sensor_type == 'soil',
            SensorReading.timestamp >= cutoff_time
        )
    ).group_by(
        func.date(SensorReading.timestamp)
    ).order_by(
        desc('date')
    ).all()

    return [{'date': r.date, 'avg_moisture': r.avg_moisture, 'reading_count': r.reading_count}
            for r in result]


def get_sensor_statistics(db: Session, user_id: int, hours: int = 24) -> dict:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    stats = db.query(
        SensorReading.sensor_type,
        func.avg(SensorReading.value).label('avg_value'),
        func.min(SensorReading.value).label('min_value'),
        func.max(SensorReading.value).label('max_value'),
        func.count(SensorReading.id).label('reading_count')
    ).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.timestamp >= cutoff_time
        )
    ).group_by(SensorReading.sensor_type).all()

    return {stat.sensor_type: {
        'average': round(stat.avg_value, 2),
        'minimum': round(stat.min_value, 2),
        'maximum': round(stat.max_value, 2),
        'readings': stat.reading_count
    } for stat in stats}


def get_zone_statistics(db: Session, user_id: int, hours: int = 24) -> dict:
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    stats = db.query(
        SensorReading.zone,
        SensorReading.sensor_type,
        func.avg(SensorReading.value).label('avg_value')
    ).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.timestamp >= cutoff_time
        )
    ).group_by(SensorReading.zone, SensorReading.sensor_type).all()

    result = {}
    for stat in stats:
        if stat.zone not in result:
            result[stat.zone] = {}
        result[stat.zone][stat.sensor_type] = round(stat.avg_value, 2)

    return result


def get_system_health(db: Session, user_id: int) -> dict:
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    twenty_four_hours_ago = now - timedelta(hours=24)

    recent_readings = db.query(SensorReading).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.timestamp >= one_hour_ago
        )
    ).count()

    active_devices = len(get_active_devices(db, user_id, hours=1))

    unacknowledged_alerts = get_unacknowledged_alerts_count(db, user_id, hours=24)

    total_readings_24h = db.query(SensorReading).filter(
        and_(
            SensorReading.user_id == user_id,
            SensorReading.timestamp >= twenty_four_hours_ago
        )
    ).count()

    expected_readings_per_hour = 12
    expected_readings_24h = expected_readings_per_hour * 24
    uptime_percentage = min(100,
                            (total_readings_24h / expected_readings_24h * 100)) if expected_readings_24h > 0 else 100

    return {
        "recent_readings": recent_readings,
        "active_devices": active_devices,
        "unacknowledged_alerts": unacknowledged_alerts,
        "uptime_percentage": round(uptime_percentage, 1),
        "last_updated": now
    }


def cleanup_old_data(db: Session, user_id: int, retention_days: int = 90):
    cutoff_time = datetime.utcnow() - timedelta(days=retention_days)

    try:
        old_readings = db.query(SensorReading).filter(
            and_(
                SensorReading.user_id == user_id,
                SensorReading.timestamp < cutoff_time
            )
        ).delete()

        old_alerts = db.query(Alert).filter(
            and_(
                Alert.user_id == user_id,
                Alert.timestamp < cutoff_time
            )
        ).delete()

        old_irrigation = db.query(IrrigationEvent).filter(
            and_(
                IrrigationEvent.user_id == user_id,
                IrrigationEvent.start_time < cutoff_time
            )
        ).delete()

        db.commit()

        logger.info(
            f"Cleaned up {old_readings} old readings, {old_alerts} old alerts, {old_irrigation} old irrigation events")

        return {
            "readings_deleted": old_readings,
            "alerts_deleted": old_alerts,
            "irrigation_events_deleted": old_irrigation
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error cleaning up old data: {e}")
        return {
            "readings_deleted": 0,
            "alerts_deleted": 0,
            "irrigation_events_deleted": 0,
            "error": str(e)
        }


def get_user_dashboard_data(db: Session, user_id: int) -> dict:
    water_stats = get_water_usage_stats(db, user_id)
    system_health = get_system_health(db, user_id)
    sensor_stats = get_sensor_statistics(db, user_id)
    zone_stats = get_zone_statistics(db, user_id)
    recent_alerts = get_alerts(db, user_id, acknowledged=False, hours=24)

    return {
        "water_usage": water_stats,
        "system_health": system_health,
        "sensor_statistics": sensor_stats,
        "zone_statistics": zone_stats,
        "recent_alerts": [{
            "id": alert.id,
            "reason": alert.reason,
            "severity": alert.severity,
            "timestamp": alert.timestamp.isoformat(),
            "zone": alert.zone,
            "sensor_type": alert.sensor_type
        } for alert in recent_alerts],
        "last_updated": datetime.utcnow().isoformat()
    }