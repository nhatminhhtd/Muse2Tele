@echo off
rem Mo FoxProfile, cho API san sang roi mo bot, moi cai 1 cua so.
cd /d "%~dp0"
start "Muse2tele_FoxProfile" cmd /c start_foxprofile.bat
echo Cho FoxProfile API (http://127.0.0.1:8010)...
:wait
timeout /t 3 /nobreak >nul
powershell -NoProfile -Command "try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 3 http://127.0.0.1:8010/api/v1/health | Out-Null; exit 0 } catch { exit 1 }"
if errorlevel 1 goto wait
start "Muse2tele_Bot" cmd /c start_bot.bat
