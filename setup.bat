@echo off
chcp 65001 >nul
rem Cai 1 lan: tao .venv, cai thu vien cho FoxProfile + bot, tai trinh duyet Camoufox.
cd /d "%~dp0"
set "BASE=python"
if exist "%LOCALAPPDATA%\Python\bin\python3.exe" set "BASE=%LOCALAPPDATA%\Python\bin\python3.exe"
"%BASE%" --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo  CHUA CAI PYTHON.
  echo  1. Vao https://www.python.org/downloads/ bam "Download Python 3.12" ^(hoac moi hon^).
  echo  2. Chay file vua tai, TICK o "Add python.exe to PATH" roi bam "Install Now".
  echo  3. Cai xong, chay lai setup.bat.
  echo.
  start "" https://www.python.org/downloads/
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" "%BASE%" -m venv .venv || goto :fail
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :fail
".venv\Scripts\python.exe" -m camoufox fetch || goto :fail
if not exist ".env" copy ".env.example" ".env" >nul
echo.
echo  CAI DAT XONG. Bay gio chay start_all.bat
pause
exit /b 0
:fail
echo.
echo  CAI DAT LOI. Kiem tra mang Internet roi chay lai setup.bat. Neu van loi, chup man hinh nay gui nguoi ho tro.
pause
exit /b 1
