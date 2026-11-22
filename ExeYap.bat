@echo off
cd /d "%~dp0"
echo Yansit.exe olusturuluyor...
python -m pip install --upgrade pyinstaller -r requirements.txt
python -m PyInstaller --noconfirm --onefile --windowed --collect-all customtkinter --hidden-import segno --icon assets\yansit.ico --add-data "assets;assets" --name "Yansit" yansit.py
copy /y "dist\Yansit.exe" "Yansit.exe" >nul
rmdir /s /q build 2>nul
del Yansit.spec 2>nul
echo Hazir: Yansit.exe
pause
