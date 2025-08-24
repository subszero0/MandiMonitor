@echo off
cd /d "%~dp0"
echo ========================================
echo   MandiMonitor Bot Launcher
echo ========================================
echo.

echo [1/3] Checking directory...
if not exist "bot\main.py" (
    echo ERROR: bot\main.py not found. Make sure you're in the MandiMonitor directory.
    pause
    exit /b 1
)
echo ✓ Found bot files

echo.
echo [2/3] Checking Python...
"%USERPROFILE%\.pyenv\pyenv-win\versions\3.11.9\python.exe" --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_PATH=%USERPROFILE%\.pyenv\pyenv-win\versions\3.11.9\python.exe
    echo ✓ Found Python 3.11.9
    goto :run_bot
)

echo Python 3.11.9 not found, trying system Python...
python --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set PYTHON_PATH=python
    echo ✓ Found system Python
    goto :run_bot
)

echo ERROR: No Python found. Install Python 3.11+ first.
pause
exit /b 1

:run_bot
echo.
echo [3/3] Starting bot...
echo Using Python: %PYTHON_PATH%
echo.
echo ========================================
echo Bot starting... Press Ctrl+C to stop
echo Health: http://localhost:8000/health
echo ========================================
echo.

"%PYTHON_PATH%" -m pip install python-telegram-bot fastapi uvicorn redis sqlmodel requests beautifulsoup4 lxml scikit-learn pandas numpy amazon-paapi >nul 2>&1

"%PYTHON_PATH%" -m bot.main

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ========================================
    echo ERROR: Bot failed to start
    echo ========================================
    echo.
    echo Common fixes:
    echo 1. Install dependencies: pip install -r requirements.txt
    echo 2. Check .env file exists with TELEGRAM_TOKEN
    echo 3. Ensure Python 3.11+ is installed
    echo.
    pause
)
