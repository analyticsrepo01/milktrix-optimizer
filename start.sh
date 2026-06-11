#!/bin/bash
echo "=== Starting Milktrix S&OP Optimization System ==="
cd /home/jupyter/milktrix_optimisation/backend

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate and install requirements
echo "Installing dependencies..."
source venv/bin/activate
pip install -r requirements.txt

# Start backend server
echo "Starting FastAPI server with built-in Premium Dashboard on http://localhost:8000"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
