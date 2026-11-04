@echo off
rem FoxProfile (app desktop + API http://127.0.0.1:8010). Du lieu profile nam o foxprofile\data.
call "%~dp0_python.bat"
cd /d "%~dp0foxprofile\data"
"%PY%" ..\repo\src\main.py
