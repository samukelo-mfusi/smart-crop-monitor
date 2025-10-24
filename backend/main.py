from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
import asyncio
import logging
from datetime import datetime
import os

# Import your modules
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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Vercel-compatible database setup
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.warning(f"Database setup warning: {e}")

security = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Vercel-compatible background task management
background_tasks = set()

async def startup_event():
    """Startup tasks adapted for Vercel"""
    logger.info("Starting IoT Smart Crop Monitoring System on Vercel")
    logger.info(f"Version: {settings.VERSION}")
    
    # Initialize communication protocols (with Vercel adaptations)
    logger.info("Initializing communication protocols...")
    
    try:
        protocols_initialized = await protocol_manager.initialize_protocols()
        if not protocols_initialized:
            logger.warning("Some communication protocols failed to initialize")
    except Exception as e:
        logger.warning(f"Protocol initialization warning: {e}")

    # Initialize services
    logger.info("Initializing services...")
    data_service = DataService()
    simulation_service = SimulationService()

    # Register protocol message handlers
    try:
        protocol_manager.register_message_handler('commands', data_service.handle_protocol_command)
        protocol_manager.register_message_handler('sensor_data', data_service.handle_incoming_sensor_data)
        protocol_manager.register_message_handler('alerts', data_service.handle_incoming_alert)
        logger.info("Message handlers registered successfully")
    except Exception as e:
        logger.warning(f"Message handler registration warning: {e}")

    # Start background tasks (Vercel-compatible)
    if not os.environ.get('VERCEL'):
        # Only start intensive background tasks if not on Vercel
        # or use Vercel-compatible alternatives
        logger.info("Starting background tasks...")
        try:
            data_task = asyncio.create_task(data_service.start_periodic_data_collection())
            simulation_task = asyncio.create_task(simulation_service.start_simulation_cycle())
            
            # Add to background tasks set to prevent garbage collection
            background_tasks.add(data_task)
            background_tasks.add(simulation_task)
            data_task.add_done_callback(background_tasks.discard)
            simulation_task.add_done_callback(background_tasks.discard)
            
            logger.info("Background tasks started")
        except Exception as e:
            logger.warning(f"Background task startup warning: {e}")

    logger.info("System startup completed")

async def shutdown_event():
    """Shutdown tasks for Vercel"""
    logger.info("Shutting down IoT Smart Crop Monitoring System...")
    
    # Cancel background tasks
    for task in background_tasks:
        task.cancel()
    
    try:
        await protocol_manager.shutdown()
        logger.info("System shutdown completed")
    except Exception as e:
        logger.warning(f"Shutdown warning: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await startup_event()
    yield
    # Shutdown
    await shutdown_event()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="IoT Smart Crop Monitoring System",
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501", "http://localhost:3000", "http://localhost:8000", "https://smart-crop-monitor.streamlit.app","https://smart-crop-monitor-backend.vercel.app"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["authentication"])
app.include_router(sensor_data.router, prefix="/api", tags=["sensor data"])
app.include_router(alerts.router, prefix="/api", tags=["alerts"])
app.include_router(system.router, prefix="/api", tags=["system"])

@app.get("/")
async def root():
    return {
        "message": "IoT Smart Crop Monitoring System API",
        "version": settings.VERSION,
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "deployment": "vercel"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION
    }

@app.get("/system/status")
async def system_status():
    """Simplified system status for Vercel"""
    return {
        "system": "operational",
        "timestamp": datetime.now().isoformat(),
        "version": settings.VERSION,
        "deployment": "vercel"
    }

# Add this for Vercel compatibility
app = app
