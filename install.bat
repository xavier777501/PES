@echo off
echo ===================================
echo   Installation Backend
echo ===================================
echo.

REM Créer venv
python -m venv venv

REM Activer
call venv\Scripts\activate

REM Upgrade pip
python -m pip install --upgrade pip

REM Installer une par une pour voir l'erreur
echo Installation FastAPI...
pip install fastapi==0.115.12

echo Installation Uvicorn...
pip install uvicorn[standard]==0.34.0

echo Installation python-multipart...
pip install python-multipart==0.0.20

echo Installation NumPy...
pip install numpy==1.26.4

echo Installation Pillow...
pip install pillow==11.1.0

echo Installation MediaPipe...
pip install "mediapipe>=1.0.0"

echo Installation OpenCV (peut prendre du temps)...
pip install opencv-python==4.10.0.84

echo.
echo ===================================
echo   Installation terminee !
echo ===================================
pause
