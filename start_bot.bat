@echo off
rem Bot Telegram <-> muse.ai. Can FoxProfile dang chay (start_foxprofile.bat).
call "%~dp0_python.bat"
cd /d "%~dp0muse_telebot"
"%PY%" muse_telebot.py
