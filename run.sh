#!/bin/bash

# Facial Recognition Attendance System Run Script
# This script activates the virtual environment and runs the system

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run ./install.sh first."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if dependencies are installed
python -c "import cv2, face_recognition, flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Dependencies not found. Please run ./install.sh first."
    exit 1
fi

# Parse command line arguments
MODE=${1:-web}
HOST=${2:-0.0.0.0}
PORT=${3:-5000}

echo "=== Facial Recognition Attendance System ==="
echo "Mode: $MODE"
echo "Host: $HOST"
echo "Port: $PORT"
echo ""

case $MODE in
    web)
        echo "Starting web interface..."
        echo "Access the system at: http://$HOST:$PORT"
        python main.py --mode web --host $HOST --port $PORT
        ;;
    cli)
        echo "Starting CLI interface..."
        python main.py --mode cli
        ;;
    attendance)
        echo "Starting attendance system..."
        python main.py --mode attendance
        ;;
    *)
        echo "Usage: ./run.sh [mode] [host] [port]"
        echo "Modes: web, cli, attendance"
        echo "Example: ./run.sh web localhost 8080"
        exit 1
        ;;
esac 