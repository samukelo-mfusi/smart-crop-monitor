import os
import sys
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")


def fix_streamlit_imports():
    """Fix Streamlit imports in PyInstaller bundle"""
    if getattr(sys, 'frozen', False):
        # Running in PyInstaller bundle
        bundle_dir = sys._MEIPASS

        # Fix for importlib.metadata
        try:
            from importlib.metadata import metadata, version, distributions
        except ImportError:
            from importlib_metadata import metadata, version, distributions

        # Add bundle directory to path for resource loading
        if bundle_dir not in sys.path:
            sys.path.insert(0, bundle_dir)

        # Fix Streamlit config discovery
        os.environ['STREAMLIT_SHARED_SECRET_KEY'] = 'pyinstaller-bundle'
        os.environ['STREAMLIT_SERVER_ENABLE_STATIC_SERVING'] = 'true'

        print("Streamlit runtime hook applied successfully")


fix_streamlit_imports()
