@echo off
cd /d "%~dp0"
if exist "Yansit.exe" ( start "" "Yansit.exe" & exit /b )
where pythonw >nul 2>nul
if errorlevel 1 (
  echo Python bulunamadi. https://www.python.org/downloads/ adresinden kurun.
  echo Kurulumda "Add Python to PATH" kutusunu isaretleyin.
  pause
  exit /b
)
python -c "import customtkinter, segno" 2>nul || python -m pip install --quiet -r requirements.txt
start "" pythonw yansit.py
