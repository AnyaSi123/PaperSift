@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Create .venv first: python -m venv .venv
  exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-build.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m PyInstaller --noconfirm PaperSift.spec
if errorlevel 1 exit /b 1
powershell -NoProfile -Command "Compress-Archive -LiteralPath 'dist\PaperSift' -DestinationPath 'dist\PaperSift-Windows.zip' -Force"
if errorlevel 1 exit /b 1
echo Ready: dist\PaperSift-Windows.zip
