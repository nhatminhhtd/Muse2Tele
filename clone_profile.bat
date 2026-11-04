@echo off
rem Clone 1 profile qua API FoxProfile cua Muse2tele (FoxProfile phai dang chay).
rem   clone_profile.bat <profile nguon> <ten moi> [--no-data] [--same-fingerprint]
rem Mac dinh: chep du lieu trinh duyet (cookie, dang nhap, tab) va tao fingerprint moi.
call "%~dp0_python.bat"
"%PY%" "%~dp0clone_profile.py" %*
