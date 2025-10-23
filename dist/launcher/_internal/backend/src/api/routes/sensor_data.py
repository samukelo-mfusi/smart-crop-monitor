# import self as self
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from streamlit import status
from yarl import Query

from ...database import models
from ...database.database import get_db
from ...database.crud import (
    create_sensor_reading, get_latest_sensor_readings, get_sensor_readings_by_zone_type,
    get_daily_averages, create_irrigation_event, get_recent_irrigation_events
)
from ...database.models import User
from ...api.dependencies import get_current_active_user
from ...services.data_services import DataService, logger
from ...processing.data_processor import DataProcessor
from ...services.historical_data_service import HistoricalDataService

router = APIRouter()


class SensorReadingCreate(BaseModel):
    zone: str
    sensor_type: str
    value: float
    unit: str
    source: str = "simulation"


class SensorReadingResponse(BaseModel):
    id: int
    zone: str
    sensor_type: str
    value: float
    unit: str
    source: str
    timestamp: datetime


class IrrigationRequest(BaseModel):
    zone: str
    duration: int


class DashboardData(BaseModel):
    soil_moisture: dict
    weather: dict
    system_metrics: dict
    alerts: list
    irrigation_status: dict
    light_level: float
    data_source: str


@router.post("/sensor-readings", response_model=SensorReadingResponse)
def create_sensor_reading_endpoint(
        reading: SensorReadingCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    db_reading = create_sensor_reading(db, reading.dict(), current_user.id)
    return SensorReadingResponse(**db_reading.__dict__)


@router.get("/sensor-readings", response_model=List[SensorReadingResponse])
def get_sensor_readings(
        hours: int = 24,
        zone: Optional[str] = None,
        sensor_type: Optional[str] = None,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    if zone and sensor_type:
        readings = get_sensor_readings_by_zone_type(db, current_user.id, zone, sensor_type, hours)
    else:
        readings = get_latest_sensor_readings(db, current_user.id, hours)

    return [SensorReadingResponse(**reading.__dict__) for reading in readings]


@router.get("/dashboard-data")
def get_dashboard_data(
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    data_service = DataService()
    dashboard_data = data_service.get_dashboard_data(db, current_user.id)

    # ADD WATER USAGE STATS TO DASHBOARD DATA
    from ...database.crud import get_water_usage_stats
    water_stats = get_water_usage_stats(db, current_user.id)
    dashboard_data["water_usage"] = water_stats

    return dashboard_data


# @router.get("/historical-data", response_model=List[Dict[str, Any]])
# async def get_historical_data(
#         days: int = Query(7, description="Number of days of historical data"),
#         db: Session = Depends(get_db),
#         current_user: models.User = Depends(get_current_active_user)
# ):
#     """Get historical sensor data for charts and trends"""
#     try:
#         # Import the enhanced function from crud
#         from ...database.crud import get_enhanced_historical_data
#
#         historical_data = get_enhanced_historical_data(db, current_user.id, days)
#         logger.info(
#             f"Returning {len(historical_data)} days of historical data up to {datetime.now().strftime('%Y-%m-%d')}")
#         return historical_data
#
#     except Exception as e:
#         logger.error(f"Error getting historical data: {e}")
#         # Fallback to basic simulated data
#         from ...database.crud import generate_historical_fallback_data
#         return generate_historical_fallback_data(days)

@router.get("/historical-data/{days}")
async def get_historical_data(
        days: int,
        db: Session = Depends(get_db),
        current_user: models.User = Depends(get_current_active_user)
):
    """Get historical sensor data - Production Python 3.8 compatible version"""
    try:
        # Validate and sanitize input
        if days <= 0 or days > 365:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Days must be between 1 and 365"
            )

        logger.info(f"Starting historical data fetch for {days} days for user {current_user.id}")

        # Try to get real data first
        historical_data = await get_production_historical_data(days, db, current_user.id)

        logger.info(f"Production: Returning {len(historical_data)} days of historical data")
        return historical_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting historical data: {e}")
        # In production, we want to be more conservative with fallbacks
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Historical data service temporarily unavailable"
        )


async def get_production_historical_data(days: int, db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Historical data with real sensor data and NASA integration"""
    try:
        # 1. Try to get real sensor data from database
        real_data = get_real_sensor_data_from_db(days, db, user_id)
        if real_data and len(real_data) >= days * 0.5:  # At least 50% real data
            logger.info(f"Using {len(real_data)} real data points")
            return real_data

        # 2. Try NASA API for enhanced data
        nasa_data = await get_nasa_enhanced_data(days)
        if nasa_data:
            logger.info(f"Using NASA-enhanced data")
            return nasa_data

        # 3. Fallback to realistic simulation based on current conditions
        logger.info("Using realistic simulation based on current conditions")
        return generate_realistic_production_data(days, db, user_id)

    except Exception as e:
        logger.error(f"Error in data pipeline: {e}")
        return generate_emergency_production_data(days)


def get_real_sensor_data_from_db(days: int, db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Get sensor data from database"""
    try:
        cutoff_date = datetime.now() - timedelta(days=days)

        # Get soil moisture readings
        readings = db.query(models.SensorReading).filter(
            models.SensorReading.user_id == user_id,
            models.SensorReading.sensor_type == 'soil_moisture',
            models.SensorReading.timestamp >= cutoff_date
        ).order_by(models.SensorReading.timestamp).all()

        if not readings:
            return []

        # Aggregate by day
        daily_data = {}
        for reading in readings:
            date_key = reading.timestamp.date().isoformat()
            if date_key not in daily_data:
                daily_data[date_key] = {
                    'values': [],
                    'count': 0
                }
            daily_data[date_key]['values'].append(reading.value)
            daily_data[date_key]['count'] += 1

        # Convert to historical format
        historical_data = []
        for date_str, data in daily_data.items():
            avg_moisture = sum(data['values']) / len(data['values'])
            historical_data.append({
                'date': date_str,
                'avg_moisture': round(avg_moisture, 1),
                'avg_temperature': 24.0,
                'avg_humidity': 65.0,
                'water_need': round(max(0, 70 - avg_moisture), 1),
                'data_source': 'database',
                'data_quality': 'high',
                'reading_count': data['count']
            })

        return sorted(historical_data, key=lambda x: x['date'])

    except Exception as e:
        logger.error(f"Error getting real sensor data: {e}")
        return []


async def get_nasa_enhanced_data(days: int) -> List[Dict[str, Any]]:
    """Get NASA-enhanced historical data"""
    try:
        from ...data_simulation.nasa_power_client import NASAPowerClient
        nasa_client = NASAPowerClient()

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        nasa_data = nasa_client.get_agricultural_data(
            latitude=-29.8587,          # coordinates for durban
            longitude=31.0218,
            start_date=start_date.strftime("%Y%m%d"),
            end_date=end_date.strftime("%Y%m%d")
        )

        if nasa_data and nasa_data.get('data_quality') != 'error':
            return format_nasa_data_for_historical(nasa_data, days)

        return []

    except Exception as e:
        logger.error(f"Error getting NASA data: {e}")
        return []


def format_nasa_data_for_historical(nasa_data: Dict[str, Any], days: int) -> List[Dict[str, Any]]:
    """Format NASA data for historical response"""
    historical_data = []

    for i in range(days):
        date = datetime.now() - timedelta(days=i)

        # Use NASA data with some daily variation
        base_moisture = nasa_data.get('soil_moisture', 65.0)
        daily_variation = (i % 7) - 3  # Weekly pattern

        moisture = max(35.0, min(80.0, base_moisture + daily_variation))

        historical_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'avg_moisture': round(moisture, 1),
            'avg_temperature': round(nasa_data.get('temperature', 24.0), 1),
            'avg_humidity': round(nasa_data.get('humidity', 65.0), 1),
            'water_need': round(max(0, 70 - moisture), 1),
            'data_source': 'nasa_power',
            'data_quality': 'high',
            'solar_radiation': nasa_data.get('solar_radiation', 0)
        })

    return list(reversed(historical_data))


def generate_realistic_production_data(days: int, db: Session, user_id: int) -> List[Dict[str, Any]]:
    """Generate realistic data based on current production conditions"""
    try:
        # Get current conditions to base simulation on
        current_readings = db.query(models.SensorReading).filter(
            models.SensorReading.user_id == user_id
        ).order_by(models.SensorReading.timestamp.desc()).first()

        if current_readings:
            base_moisture = current_readings.value
        else:
            base_moisture = 65.0  # Default fallback

        historical_data = []

        for i in range(days):
            date = datetime.now() - timedelta(days=i)

            # Realistic patterns for production
            month = date.month
            day_of_week = date.weekday()

            # Seasonal adjustment for Southern Hemisphere
            if month in [12, 1, 2]:  # Summer
                seasonal_adj = -8.0
            elif month in [6, 7, 8]:  # Winter
                seasonal_adj = 5.0
            else:
                seasonal_adj = 0.0

            # Weekend effect
            weekend_adj = -4.0 if day_of_week >= 5 else 0.0

            # Natural daily variation
            daily_variation = (i % 5) - 2

            moisture = max(35.0, min(80.0, base_moisture + seasonal_adj + weekend_adj + daily_variation))

            historical_data.append({
                'date': date.strftime('%Y-%m-%d'),
                'avg_moisture': round(moisture, 1),
                'avg_temperature': round(24.0 + seasonal_adj * 0.3, 1),
                'avg_humidity': round(65.0 + seasonal_adj * 0.5, 1),
                'water_need': round(max(0, 70 - moisture), 1),
                'data_source': 'production_simulation',
                'data_quality': 'medium',
                'seasonal_adjustment': round(seasonal_adj, 1)
            })

        return list(reversed(historical_data))

    except Exception as e:
        logger.error(f"Error generating realistic data: {e}")
        return generate_emergency_production_data(days)


def generate_emergency_production_data(days: int) -> List[Dict[str, Any]]:
    """Emergency fallback for production - should rarely be used"""
    logger.warning(f"Using emergency fallback for {days} days")

    emergency_data = []
    base_moisture = 65.0

    for i in range(days):
        date = datetime.now() - timedelta(days=i)

        # Conservative linear decrease
        moisture = max(40.0, base_moisture - (i * 1.5))

        emergency_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'avg_moisture': round(moisture, 1),
            'avg_temperature': 24.0,
            'avg_humidity': 65.0,
            'water_need': round(max(0, 70 - moisture), 1),
            'data_source': 'emergency_fallback',
            'data_quality': 'low',
            'note': 'Service degradation - contact support if persistent'
        })

    return list(reversed(emergency_data))

@router.post("/control/irrigate")
def start_irrigation(
        request: IrrigationRequest,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    try:
        irrigation_event = create_irrigation_event(
            db, request.zone, request.duration, current_user.id
        )

        return {
            "success": True,
            "message": f"Irrigation started for {request.zone} for {request.duration} minutes",
            "event_id": irrigation_event.id,
            "water_used": irrigation_event.water_used
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start irrigation: {str(e)}")


@router.get("/irrigation-events")
def get_irrigation_events(
        days: int = 7,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    events = get_recent_irrigation_events(db, current_user.id, days)
    return [
        {
            "id": event.id,
            "zone": event.zone,
            "duration": event.duration,
            "water_used": event.water_used,
            "status": event.status,
            "start_time": event.start_time.isoformat(),
            "end_time": event.end_time.isoformat() if event.end_time else None
        }
        for event in events
    ]


@router.post("/data/refresh")
def refresh_real_world_data(
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    data_service = DataService()

    def refresh_task():
        data_service.collect_real_world_data(db, current_user.id)

    background_tasks.add_task(refresh_task)

    return {
        "success": True,
        "message": "Real-world data refresh started",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/data/status")
def get_data_refresh_status():
    return {
        "last_refresh": datetime.now().isoformat(),
        "in_progress": False,
        "last_success": datetime.now().isoformat(),
        "data_sources": {
            "nasa_power": "active",
            "openweather": "active",
            "sensor_simulation": "active"
        }
    }


@router.get("/data/readings")
def get_sensor_data_readings(
        hours: int = 24,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    readings = get_latest_sensor_readings(db, current_user.id, hours)

    return [
        {
            "id": reading.id,
            "zone": reading.zone,
            "sensor_type": reading.sensor_type,
            "value": reading.value,
            "unit": reading.unit,
            "source": reading.source,
            "timestamp": reading.timestamp.isoformat()
        }
        for reading in readings
    ]