@echo off
setlocal
cd /d %~dp0\..

python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install pyinstaller

if not exist build mkdir build
if not exist dist mkdir dist

pyinstaller --noconfirm --clean --name ANNE --onedir desktop\anne_launcher.py

echo.
echo ANNE Windows build completed.
echo Output: dist\ANNE\
pause
