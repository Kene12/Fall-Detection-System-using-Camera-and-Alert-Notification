#!/bin/bash

echo "Starting setup for YOLO-based Fall Detection System..."

# Update system packages
echo "Updating system..."
sudo apt update && sudo apt upgrade -y

# Install dependencies
echo "Installing dependencies..."
sudo apt install -y python3-pip python3-opencv ffmpeg libsm6 libxext6

# Install virtual environment (optional but recommended)
echo "Creating virtual environment..."
python3 -m venv fall_detection_env
source fall_detection_env/bin/activate

# Install Python packages
echo "Installing required Python packages..."
pip install --upgrade pip
pip install opencv-python numpy requests Flask firebase-admin ultralytics jwt schedule torch torchvision torchaudio matplotlib

# Install TensorRT (specific for Jetson)
if [[ $(uname -m) == "aarch64" ]]; then
    echo "Detected Jetson system. Installing TensorRT and Jetson dependencies..."
    sudo apt install -y python3-libnvinfer-dev
fi

# Setup complete
echo "Setup complete! Use 'source fall_detection_env/bin/activate' to activate the virtual environment."