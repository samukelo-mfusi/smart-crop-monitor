# IoT-Based Smart Crop Monitoring System

A complete implementation of an IoT-based smart crop monitoring system that leverages real-time meteorological data from authoritative APIs to provide actionable insights for sustainable agriculture. This system eliminates the need for expensive physical hardware while maintaining scientific credibility through sophisticated data processing.

## Features

- **Real-time Meteorological Data**: Integration with NASA POWER and OpenWeatherMap APIs
- **Advanced Data Processing**: Environmental models for soil moisture estimation, anomaly detection
- **Multiple Communication Protocols**: MQTT, HTTP, and COAP support
- **Cost-Effective Solution**: No physical hardware required
- **User-Friendly Interface**: Streamlit-based dashboard with real-time visualizations
- **Scientific Validation**: ≤5% mean absolute error compared to ground-truth data

## Requirements

- Python 3.8+
- FastAPI
- Streamlit
- NASA POWER API access
- OpenWeatherMap API key (optional)

## Quick Start

### Installation

1. **Clone the repository**:


git clone https://github.com/samukelo-mfusi/smart-crop-monitor.git

cd smart-crop-monitor



2. **Set up environment variables**:

python -m venv .venv       

.venv\Scripts\Activate.ps1


3. **Install dependencies**:

pip install -r requirements.txt


## REGISTER AND LOGIN - Click on the live link below

https://smart-crop-monitor.streamlit.app/



## Available Accounts: Use to login

username: samukelo

password: Samukelo@01




## EXECUTABLE:

The exe app is located in the dist/launcher folder. Double click on it to run the app. If it doesn`t run use the link https://smart-crop-monitor.streamlit.app/ (Recommended). Create accoount or use the above login details.


3. **Set up environment variables**:

python -m venv .venv       

.venv\Scripts\Activate.ps1
  


### Running the Application

**Method 1: Unified Launcher (Recommended)**

cd backend 

cd fronted (In a different terminal)


**Method 2: Individual Services**
bash
# Terminal 1 - Backend
python run_system.py   

# Terminal 2 - Frontend
streamlit run dashboard.py

*Run executable in the dist folder*

The application will be available at:
- **Frontend**: http://localhost:8501
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs



## System Architecture

The system follows a modular 4-layer architecture:

1. **Data Acquisition Layer**: NASA POWER and OpenWeatherMap API integration
2. **Data Processing Layer**: Environmental models and anomaly detection
3. **Communication Layer**: MQTT/HTTP/COAP protocol support
4. **Application Layer**: FastAPI backend and Streamlit frontend

## Configuration

Edit `config/settings.py` to customize:

- API endpoints and keys
- Data processing parameters
- Communication protocol settings
- Evaluation metrics thresholds

## API Endpoints

### Data Endpoints
- `GET /api/health` - System health check
- `GET /api/weather/{latitude}/{longitude}` - Get weather data
- `POST /api/process` - Process meteorological data
- `GET /api/history` - Get historical data

### Authentication
- `POST /api/auth/token` - Generate JWT token
- `POST /api/auth/validate` - Validate token
