@echo off
echo Starting setup for YOLO-based Fall Detection System...

:: Update pip and install dependencies
python -m pip install --upgrade pip
python -m pip install opencv-python numpy requests Flask firebase-admin ultralytics jwt schedule torch torchvision torchaudio matplotlib

echo Setup complete!
pause