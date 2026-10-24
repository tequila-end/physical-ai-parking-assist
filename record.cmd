@echo off
setlocal
cd /d "%~dp0"
set "PARKING_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%PARKING_PY%" set "PARKING_PY=%~dp0..\..\work\.venv\Scripts\python.exe"
if not exist "%PARKING_PY%" (
  echo Run setup.cmd first. Python 3.11 is required.
  pause
  exit /b 1
)
"%PARKING_PY%" -X utf8 demo.py --record
pause
