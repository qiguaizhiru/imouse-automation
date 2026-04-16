@echo off
title iMouse Pro V2.0
cd /d "%~dp0"

set PY=

python --version >nul 2>nul
if not errorlevel 1 set PY=python
if defined PY goto RUN

py -3.12 --version >nul 2>nul
if not errorlevel 1 set PY=py -3.12
if defined PY goto RUN

py -3 --version >nul 2>nul
if not errorlevel 1 set PY=py -3
if defined PY goto RUN

echo [ERROR] Python not found! Run install.bat first.
pause
exit /b 1

:RUN
%PY% imouse6.16.py
if errorlevel 1 (
    echo.
    echo [ERROR] Program crashed. Run install.bat if modules are missing.
    pause
)
