@echo off
echo ===================================
echo   PES Face UV - Backend Python
echo ===================================
echo.

REM Vérifier si venv existe
if not exist "venv\" (
    echo Creation de l'environnement virtuel...
    python -m venv venv
    echo.
)

REM Activer venv
call venv\Scripts\activate

REM Installer/mettre à jour les dépendances
echo Installation des dependances...
pip install -r requirements.txt --quiet
echo.

REM Créer dossier temp si nécessaire
if not exist "temp\" mkdir temp

REM Lancer le serveur
echo Demarrage du serveur FastAPI...
echo URL: http://localhost:8000
echo Docs: http://localhost:8000/docs
echo.
python main.py
