import os
import sys
import subprocess
import time
import threading
import webbrowser


def install_packages():
    """Install required packages"""
    packages = [
        'uvicorn', 'fastapi', 'streamlit', 'requests',
        'pandas', 'plotly', 'python-dotenv', 'scikit-learn'
    ]

    for package in packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package} already installed")
        except ImportError:
            print(f"Installing {package}...")
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', package])


def start_backend():
    """Start FastAPI backend using run_system.py"""
    print("Starting backend server on http://localhost:8000")
    if os.path.exists('backend/run_system.py'):
        backend_process = subprocess.Popen([sys.executable, 'run_system.py'], cwd='backend')
    else:
        print("ERROR: backend/run_system.py not found!")
        return None
    return backend_process


def start_frontend():
    """Start Streamlit frontend"""
    time.sleep(5)  # Wait for backend to start
    print("Starting frontend dashboard on http://localhost:8501")
    if os.path.exists('frontend/dashboard.py'):
        frontend_process = subprocess.Popen([
            sys.executable, '-m', 'streamlit', 'run', 'dashboard.py',
            '--server.port', '8501', '--server.headless', 'true'
        ], cwd='frontend')
    else:
        print("ERROR: frontend/dashboard.py not found!")
        return None
    return frontend_process


def open_browser():
    """Open browser after delay"""
    time.sleep(8)
    print("Opening dashboard in your browser...")
    webbrowser.open('http://localhost:8501')


def main():
    print("🌱 Smart Irrigation System - Starting...")
    print("Installing dependencies...")

    # Install packages
    install_packages()

    # Ensure directories exist
    os.makedirs('backend', exist_ok=True)
    os.makedirs('frontend', exist_ok=True)

    # Check if required files exist
    if not os.path.exists('backend/run_system.py'):
        print("ERROR: backend/run_system.py not found!")
        print("Please make sure run_system.py is in the backend/ folder")
        input("Press Enter to exit...")
        return

    if not os.path.exists('frontend/dashboard.py'):
        print("ERROR: frontend/dashboard.py not found!")
        print("Please make sure dashboard.py is in the frontend/ folder")
        input("Press Enter to exit...")
        return

    # Start services
    backend_proc = start_backend()
    if backend_proc is None:
        return

    frontend_proc = start_frontend()
    if frontend_proc is None:
        backend_proc.terminate()
        return

    # Open browser
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()

    print("\n" + "=" * 50)
    print("System is running!")
    print("Dashboard: http://localhost:8501")
    print("API Docs: http://localhost:8000/docs")
    print("Press Ctrl+C to stop the system")
    print("=" * 50)

    try:
        # Keep the main thread alive
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()
        print("System stopped.")


if __name__ == "__main__":
    main()
