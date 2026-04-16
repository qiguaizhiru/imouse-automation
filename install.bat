@echo off
title iMouse Pro V2.0 - Setup
color 0A
echo ============================================
echo   iMouse Pro V2.0 - Environment Setup
echo ============================================
echo.

set PY=

python --version >nul 2>nul
if not errorlevel 1 set PY=python
if defined PY goto CHECK

py -3.12 --version >nul 2>nul
if not errorlevel 1 set PY=py -3.12
if defined PY goto CHECK

py -3 --version >nul 2>nul
if not errorlevel 1 set PY=py -3
if defined PY goto CHECK

echo [ERROR] Python not found!
echo Please install Python 3.12
echo https://www.python.org/ftp/python/3.12.9/python-3.12.9-amd64.exe
pause
exit /b 1

:CHECK
echo Python: %PY%
%PY% --version
echo.
echo Installing dependencies...
echo.
%PY% -m pip install PyQt6 requests websocket-client pandas openpyxl opencv-python numpy Pillow pytesseract
echo.
echo Checking Tesseract OCR engine...
set TESS_DIR=C:\Program Files\Tesseract-OCR
set TESS_EXE=%TESS_DIR%\tesseract.exe

where tesseract >nul 2>nul
if not errorlevel 1 goto TESS_OK

if exist "%TESS_EXE%" goto ADD_PATH

echo.
echo [INFO] Tesseract OCR engine not found.
echo.
echo Please download and install Tesseract OCR:
echo   https://sourceforge.net/projects/tesseract-ocr.mirror/files/5.5.0/tesseract-ocr-w64-setup-5.5.0.20241111.exe/download
echo.
echo Install to default path: C:\Program Files\Tesseract-OCR\
echo Then re-run this install.bat.
echo.
echo The program will auto-detect the install path on startup.
goto DONE

:ADD_PATH
echo Adding Tesseract to PATH...
setx PATH "%PATH%;%TESS_DIR%" >nul 2>nul
set PATH=%PATH%;%TESS_DIR%
echo [OK] Tesseract path configured: %TESS_DIR%
goto DONE

:TESS_OK
echo [OK] Tesseract already in PATH.

:DONE
echo ============================================
echo   Done! Now double-click run.bat to start.
echo ============================================
pause
