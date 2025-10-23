from datetime import datetime
import uuid

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sensor_readings = relationship("SensorReading", back_populates="user")
    alerts = relationship("Alert", back_populates="user")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), default=generate_uuid, unique=True, index=True)
    zone = Column(String(20), nullable=False)  # zone1, zone2, etc.
    sensor_type = Column(String(20), nullable=False)  # soil, temperature, humidity, light
    value = Column(Float, nullable=False)
    unit = Column(String(10), nullable=False)
    source = Column(String(20), default="simulation")  # simulation, nasa_power, openweather
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # ADD THESE FIELDS:
    device_id = Column(String(50), nullable=True, index=True)  # Add device_id
    latitude = Column(Float, nullable=True)  # Add latitude
    longitude = Column(Float, nullable=True)  # Add longitude

    # Relationships
    user = relationship("User", back_populates="sensor_readings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(String(36), default=generate_uuid, unique=True, index=True)
    zone = Column(String(20))
    sensor_type = Column(String(20))
    reason = Column(String(200), nullable=False)
    severity = Column(String(20), default="warning")
    value = Column(Float)
    threshold = Column(Float)
    recommendation = Column(Text)
    acknowledged = Column(Boolean, default=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    device_id = Column(String(50), nullable=True, index=True)

    # Relationships
    user = relationship("User", back_populates="alerts")


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(50), unique=True, index=True, nullable=False)
    value = Column(String(200), nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IrrigationEvent(Base):
    __tablename__ = "irrigation_events"

    id = Column(Integer, primary_key=True, index=True)
    zone = Column(String(20), nullable=False)
    duration = Column(Integer, nullable=False)  # minutes
    water_used = Column(Float)  # liters
    status = Column(String(20), default="completed")  # scheduled, running, completed, failed
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    user_id = Column(Integer, ForeignKey("users.id"))