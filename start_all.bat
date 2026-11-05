@echo off
rem Mo FoxProfile, cho API san sang roi mo bot, moi cai 1 cua so.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Chua cai dat. Dang chay setup.bat...
  call setup.bat || exit /b 1
)
start "Muse2tele_FoxProfile" cmd /c start_foxprofile.bat
echo Dang cho FoxProfile khoi dong (http://127.0.0.1:8000)...
set "WAIT_COUNT=0"
:wait
timeout /t 3 /nobreak >nul
set /a WAIT_COUNT+=1
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:8000/api/v1/health | Out-Null; exit 0 } catch { exit 1 }"
if not errorlevel 1 goto started
if %WAIT_COUNT% GEQ 40 (
  echo FoxProfile khong len sau 120 giay. Kiem tra cua so Muse2tele_FoxProfile xem loi gi, sua xong chay lai start_all.bat.
  exit /b 1
)
goto wait
:started
start "Muse2tele_Bot" cmd /k start_bot.bat
echo Da mo FoxProfile va bot. Co the dong cua so nay.
