@echo off
rem FoxProfile (app desktop + API http://127.0.0.1:8000). Du lieu profile nam o foxprofile\data.
call "%~dp0_python.bat"
if not exist "%~dp0foxprofile\data\" mkdir "%~dp0foxprofile\data"
if errorlevel 1 exit /b 1
cd /d "%~dp0foxprofile\data"
if errorlevel 1 exit /b 1
"%PY%" ..\repo\src\main.py
