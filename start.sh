#!/bin/bash

# Use environment variable PORT for FastAPI and Streamlit
API_PORT=${API_PORT:-8080}
PORT=${PORT:-8501}

echo "Starting FastAPI on port $API_PORT..."
uvicorn backend.main:app --host 0.0.0.0 --port $API_PORT --reload &

# Wait for FastAPI to be ready before starting Streamlit
echo "Waiting for FastAPI to become available on http://localhost:$API_PORT/health ..."
until curl -s http://localhost:$API_PORT/health > /dev/null; do
  echo -n "."
  sleep 1
done

echo -e "\nFastAPI is up!"

echo "Starting Streamlit on port $PORT..."
streamlit run frontend/dashboard.py --server.port $PORT --server.headless true