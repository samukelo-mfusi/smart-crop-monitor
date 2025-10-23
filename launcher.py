import os
import sys
import subprocess
import time
import threading
import webbrowser

def install_packages():
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
    print("Starting backend server on http://127.0.0.1:8000")
    backend_script = 'run_system.py'
    backend_dir = 'backend'
    backend_path = os.path.join(backend_dir, backend_script)
    if not os.path.exists(backend_path):
        print(f"ERROR: {backend_path} not found!")
        return None
    return subprocess.Popen([sys.executable, backend_script], cwd=backend_dir)

def start_frontend():
    print("Starting frontend dashboard on http://127.0.0.1:8501")
    frontend_script = 'dashboard.py'
    frontend_dir = 'frontend'
    frontend_path = os.path.join(frontend_dir, frontend_script)
    if not os.path.exists(frontend_path):
        print(f"ERROR: {frontend_path} not found!")
        return None
    # Delay a little to give backend time to start
    time.sleep(5)
    return subprocess.Popen([
        sys.executable, '-m', 'streamlit', 'run', frontend_script,
        '--server.port', '8501', '--server.headless', 'true'
    ], cwd=frontend_dir)

def open_browser():
    time.sleep(8)
    print("Opening dashboard in your browser...")
    webbrowser.open('http://127.0.0.1:8501')

def main():
    print("🌱 Smart Crop Monitor - Starting...")
    install_packages()

    os.makedirs('backend', exist_ok=True)
    os.makedirs('frontend', exist_ok=True)

    backend_proc = start_backend()
    if backend_proc is None:
        print("Backend failed to start, exiting.")
        return

    frontend_proc = start_frontend()
    if frontend_proc is None:
        backend_proc.terminate()
        print("Frontend failed to start, exiting.")
        return

    browser_thread = threading.Thread(target=open_browser, daemon=True)
    browser_thread.start()

    print("\n" + "="*50)
    print("System is running!")
    print("Backend API: http://127.0.0.1:8000")
    print("Dashboard: http://127.0.0.1:8501")
    print("Press Ctrl+C to stop.")
    print("="*50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        backend_proc.terminate()
        frontend_proc.terminate()
        backend_proc.wait()
        frontend_proc.wait()
        print("System stopped.")

if __name__ == "__main__":
    main()
