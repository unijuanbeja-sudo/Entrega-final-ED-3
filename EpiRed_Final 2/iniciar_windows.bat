@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Iniciando EpiRed (demo academica)...
python server.py
if errorlevel 1 (
 echo Verifica que Python este instalado y agregado al PATH.
 pause
)
