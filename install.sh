#!/bin/bash

# Facial Recognition Attendance System Installation Script
# This script installs all necessary dependencies on Ubuntu/Debian systems

echo "=== Facial Recognition Attendance System Installation ==="
echo "This script will install all necessary dependencies."
echo ""

# Check if running as root (allow for sudo)
if [ "$EUID" -eq 0 ] && [ "$SUDO_USER" = "" ]; then
    echo "Please do not run this script as root."
    exit 1
fi

# Update package list
echo "1. Updating package list..."
sudo apt-get update

# Install system dependencies
echo "2. Installing system dependencies..."
sudo apt-get install -y python3-dev python3-pip
sudo apt-get install -y cmake
sudo apt-get install -y libopenblas-dev liblapack-dev
sudo apt-get install -y libx11-dev libgtk-3-dev
sudo apt-get install -y libboost-python-dev

# Install Python dependencies
echo "3. Installing Python dependencies..."
echo "Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Check if installation was successful
echo "4. Verifying installation..."
source venv/bin/activate
python -c "import cv2; import face_recognition; import flask; print('✓ All dependencies installed successfully!')"

if [ $? -eq 0 ]; then
    echo ""
    echo "=== Installation Complete ==="
echo "You can now run the system using:"
echo "  ./run.sh                     # Start the web interface"
echo "  source venv/bin/activate"
echo "  python main.py --mode web    # Web interface"
echo ""
echo "Access the system at: http://localhost:5000"
    echo ""
    echo "For more information, see README.md"
else
    echo ""
    echo "✗ Installation failed. Please check the error messages above."
    echo "You may need to install dependencies manually."
    exit 1
fi 