@echo off
echo Starting MandiMonitor Bot...
echo.

REM Try different Python/Poetry combinations
echo Attempting to start bot...

REM Method 1: Try direct poetry command
poetry run python -m bot.main 2>nul
if %ERRORLEVEL% EQU 0 goto :success

REM Method 2: Try with full path
"%USERPROFILE%\.pyenv\pyenv-win\versions\3.9.13\Scripts\poetry.exe" run python -m bot.main 2>nul
if %ERRORLEVEL% EQU 0 goto :success

REM Method 3: Try direct Python with virtual environment activation
if exist "%USERPROFILE%\AppData\Local\pypoetry\Cache\virtualenvs\mandi-monitor-bot-VH3apQq_-py3.12\Scripts\activate.bat" (
    call "%USERPROFILE%\AppData\Local\pypoetry\Cache\virtualenvs\mandi-monitor-bot-VH3apQq_-py3.12\Scripts\activate.bat"
    python -m bot.main
    goto :success
)

REM Method 4: Try any Python 3.12 installation
python.exe -m bot.main 2>nul
if %ERRORLEVEL% EQU 0 goto :success

echo.
echo ERROR: Could not start the bot. Please check:
echo 1. Poetry is installed
echo 2. Dependencies are installed (poetry install)
echo 3. Python 3.12 is available
echo 4. You're in the MandiMonitor directory
echo.
pause
goto :end

:success
echo Bot started successfully!
echo Bot is running at http://localhost:8000
echo Health endpoint: http://localhost:8000/health
echo Press Ctrl+C to stop the bot.

:end
