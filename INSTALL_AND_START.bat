@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
echo ========================================
echo   MandiMonitor Bot Setup & Launcher
echo ========================================
echo.

echo [1/4] Checking directory...
if not exist "bot\main.py" (
    echo ERROR: bot\main.py not found. Make sure you're in the MandiMonitor directory.
    pause
    exit /b 1
)
echo ✓ Found bot files

echo.
echo [2/4] Setting up Python...
REM Try Python 3.12 first (preferred)
set PYTHON_PATH=%USERPROFILE%\.pyenv\pyenv-win\versions\3.12.10\python.exe
if exist "%PYTHON_PATH%" (
    echo ✓ Found Python 3.12.10: %PYTHON_PATH%
    goto :install_deps
)

REM Try Python 3.11.9 as fallback
set PYTHON_PATH=%USERPROFILE%\.pyenv\pyenv-win\versions\3.11.9\python.exe
if exist "%PYTHON_PATH%" (
    echo ✓ Found Python 3.11.9: %PYTHON_PATH%
    echo   Note: Project prefers Python 3.12+ but 3.11.9 should work
    goto :install_deps
)

REM Try any system Python
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
    echo ✓ Found system Python: !PYTHON_VERSION!
    set PYTHON_PATH=python
    goto :install_deps
)

echo ERROR: No compatible Python found
echo Please install Python 3.11+ or 3.12+
pause
exit /b 1

:install_deps

echo.
echo [3/4] Installing dependencies...
echo This may take a few minutes...
echo.

"%PYTHON_PATH%" -m pip install --upgrade pip
echo Installing core dependencies...
"%PYTHON_PATH%" -m pip install flask python-telegram-bot fastapi uvicorn redis sqlmodel requests sqlalchemy apscheduler pydantic-settings
echo Installing ML dependencies...
"%PYTHON_PATH%" -m pip install scikit-learn pandas numpy
echo Installing Amazon PA-API (correct package name)...
"%PYTHON_PATH%" -m pip install "python-amazon-paapi>=5.0.0,<6.0.0"
echo Installing optional scraping dependencies...
"%PYTHON_PATH%" -m pip install beautifulsoup4 lxml

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo ✓ Dependencies installed

echo.
echo [4/4] Starting MandiMonitor Bot...
echo.
echo ========================================
echo Bot starting... Press Ctrl+C to stop
echo.
echo Health endpoint: http://localhost:8000/health
echo Telegram bot: @MandiMonitor_bot
echo ========================================
echo.

"%PYTHON_PATH%" -m bot.main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo ERROR: Bot failed to start
    echo ========================================
    echo.
    echo Please check:
    echo 1. .env file exists with TELEGRAM_TOKEN and PA-API credentials
    echo 2. All dependencies installed correctly
    echo 3. No other instance of the bot is running
    echo.
    pause
)
