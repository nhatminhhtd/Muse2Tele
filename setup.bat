@echo off
rem Cai 1 lan: tao .venv, cai thu vien cho FoxProfile + bot, tai trinh duyet Camoufox.
cd /d "%~dp0"
set "BASE=python"
if exist "%LOCALAPPDATA%\Python\bin\python3.exe" set "BASE=%LOCALAPPDATA%\Python\bin\python3.exe"
if not exist ".venv\Scripts\python.exe" "%BASE%" -m venv .venv || exit /b 1
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || exit /b 1
".venv\Scripts\python.exe" -m camoufox fetch
echo.
echo Xong. Chay start_all.bat
