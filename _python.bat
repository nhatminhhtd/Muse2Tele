@echo off
rem Chon Python: .venv cua Muse2tele > Python cai cho user > python trong PATH. Dat PY truoc khi goi de ep dung ban khac.
if defined PY goto :eof
if exist "%~dp0.venv\Scripts\python.exe" (set "PY=%~dp0.venv\Scripts\python.exe" & goto :eof)
if exist "%LOCALAPPDATA%\Python\bin\python3.exe" (set "PY=%LOCALAPPDATA%\Python\bin\python3.exe" & goto :eof)
set "PY=python"
