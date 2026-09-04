@echo off
echo ===================================
echo   Demarrage Backend
echo ===================================
echo.

REM Activer venv
call venv\Scripts\activate

REM Créer dossier temp
if not exist "temp\" mkdir temp

REM Lancer
echo Serveur sur http://localhost:8000
echo Docs sur http://localhost:8000/docs
echo.
echo Appuie sur Ctrl+C pour arreter
echo.
python main.py
