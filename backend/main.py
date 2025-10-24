
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime
import uvicorn

from src.core.config import settings
from src.database.database import engine, SessionLocal
from src.database.models import Base
from src.services.data_services import DataService
from src.services.simulation_service import SimulationService
from src.api.routes import auth, sensor_data, alerts, system
from src.communication import protocol_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Error creating database tables: {e}")

# Security
security = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def startup_event():
    """Startup tasks"""
    logger.info("Starting IoT Smart Crop Monitoring System")
    logger.info(f"Version: {settings.VERSION}")
    logger.info(f"Debug Mode: {settings.DEBUG}")

    # Initialize communication protocols
    logger.info("Initializing communication protocols...")
    protocols_initialized = await protocol_manager.initialize_protocols()

    if not protocols_initialized:
        logger.error("Failed to initialize communication protocols")
        raise RuntimeError("Failed to initialize communication protocols")
    else:
        logger.info("All communication protocols initialized successfully")

    # Initialize services
    logger.info("Initializing services...")
    data_service = DataService()
    simulation_service = SimulationService()

    # Register protocol message handlers
    protocol_manager.register_message_handler('commands', data_service.handle_protocol_command)
    protocol_manager.register_message_handler('sensor_data', data_service.handle_incoming_sensor_data)
    protocol_manager.register_message_handler('alerts', data_service.handle_incoming_alert)

    logger.info("Services initialized successfully")

    # Start background tasks
    logger.info("Starting background tasks...")
    asyncio.create_task(data_service.start_periodic_data_collection())
    asyncio.create_task(simulation_service.start_simulation_cycle())

    logger.info("Background tasks started")
    logger.info("System startup completed successfully")

    # Broadcast system startup status
    startup_status = {
        "status": "online",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "protocols": protocol_manager.get_protocol_status(),
        "message": "System started successfully"
    }
    await protocol_manager.broadcast_system_status(startup_status)


async def shutdown_event():
    """Shutdown tasks"""
    logger.info("Shutting down IoT Smart Crop Monitoring System...")
    await protocol_manager.shutdown()
    logger.info("System shutdown completed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    try:
        await startup_event()
    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

    yield

    # Shutdown
    await shutdown_event()


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="IoT Smart Crop Monitoring System with real-time data processing and multi-protocol communication",
    version=settings.VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:3000", "http://localhost:8000", "https://smart-crop-monitor.streamlit.app","https://smart-crop-monitor-backend.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(sensor_data.router, prefix="/api", tags=["sensor data"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(system.router, prefix="/api", tags=["system"])


@app.get("/", summary="Root endpoint", response_description="System status")
async def root():
    """Root endpoint showing system status and available protocols"""
    return {
        "message": "IoT Smart Crop Monitoring System API",
        "version": settings.VERSION,
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "protocols": protocol_manager.get_protocol_status(),
        "endpoints": {
            "api_docs": "/docs",
            "health": "/health",
            "system_status": "/system/status"
        }
    }


@app.get("/health", summary="Health check", response_description="System health status")
async def health_check():
    """Comprehensive health check endpoint"""
    protocols_status = protocol_manager.get_protocol_status()

    # Check if critical protocols are working
    critical_protocols_healthy = (
            protocols_status['mqtt']['enabled'] == protocols_status['mqtt']['connected'] and
            protocols_status['http']['enabled'] 
            #and protocols_status['coap']['enabled'] == protocols_status['coap']['running']
    )

    health_status = "healthy" if critical_protocols_healthy else "degraded"

    return {
        "status": health_status,
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "protocols": protocols_status,
        "database": "connected",
        "external_apis": {
            "nasa_power": "available",
            "openweather": "available" if settings.OPENWEATHER_API_KEY and settings.OPENWEATHER_API_KEY != "Invalid API Key" else "Invalid Key"
        }
    }


@app.get("/system/status", summary="System status", response_description="Detailed system status")
async def system_status():
    """Detailed system status information"""
    protocols_status = protocol_manager.get_protocol_status()

    status_data = {
        "system": "operational",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "data_sources": {
            "nasa_power": "active",
            "openweather": "active" if settings.OPENWEATHER_API_KEY and settings.OPENWEATHER_API_KEY != "Invalid API Key" else "Invalid Key",
            "sensor_ingestion": "active"
        },
        "protocols": protocols_status,
        "active_protocols": protocols_status['active_protocols'],
        "metrics": {
            "data_collection_interval": settings.DATA_COLLECTION_INTERVAL,
            "data_retention_days": settings.DATA_RETENTION_DAYS,
            "alert_thresholds": {
                "soil_moisture_critical": settings.SOIL_MOISTURE_CRITICAL,
                "soil_moisture_warning": settings.SOIL_MOISTURE_WARNING,
                "temperature_critical": settings.TEMPERATURE_CRITICAL
            }
        }
    }

    # Broadcast system status via protocols
    await protocol_manager.broadcast_system_status(status_data)

    return status_data


@app.get("/protocols/status", summary="Protocols status", response_description="Detailed protocols status")
async def protocols_status():
    """Get detailed status of all communication protocols"""
    return protocol_manager.get_protocol_status()


@app.post("/system/restart-protocols", summary="Restart protocols", response_description="Protocol restart status")
async def restart_protocols():
    """Restart all communication protocols (admin function)"""
    try:
        logger.warning("Protocol restart requested via API")

        # Shutdown existing protocols
        await protocol_manager.shutdown()

        # Reinitialize protocols
        success = await protocol_manager.initialize_protocols()

        if success:
            logger.info("Protocols restarted successfully via API")
            return {
                "status": "success",
                "message": "Protocols restarted successfully",
                "timestamp": datetime.now().isoformat(),
                "protocols": protocol_manager.get_protocol_status()
            }
        else:
            logger.error("Failed to restart protocols via API")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to restart protocols"
            )

    except Exception as e:
        logger.error(f"Error restarting protocols: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error restarting protocols: {str(e)}"
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True
    )
