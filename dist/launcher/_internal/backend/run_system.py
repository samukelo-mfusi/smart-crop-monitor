import uvicorn
import logging
from main import app

# --- Safe logging config for PyInstaller builds (no console) ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    """Start the IoT monitoring system (packaged build)"""
    logger.info("Starting IoT Smart Crop Monitoring System...")
    logger.info("Backend: FastAPI + Uvicorn | Frontend: Streamlit Dashboard")
    logger.info("Dashboard URL: http://localhost:8501")

    # Custom safe configuration (no color, no TTY dependency)
    config = uvicorn.Config(
        "main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,           # Disable reload for packaged app
        access_log=True,
        use_colors=False,       # ✅ prevents isatty() error
    )

    server = uvicorn.Server(config)
    server.run()

if __name__ == "__main__":
    main()

