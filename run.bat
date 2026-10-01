@echo off
chcp 65001 > nul
cd /d "%~dp0"

set PYTHON_PATH=C:\Users\aland\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe

if not exist "%PYTHON_PATH%" (
    set PYTHON_PATH=python
)

"%PYTHON_PATH%" launcher.py %*
pause
