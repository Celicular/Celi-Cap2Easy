@echo off
echo Starting Video Captioning Tool...

:: Check if Python is installed
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Check if requirements are installed
pip show PyQt6 > nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required packages...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo Failed to install requirements!
        pause
        exit /b 1
    )
)

:: Run the application
python caption-tool/main.py

:: If application exits with an error
if %errorlevel% neq 0 (
    echo Application exited with an error. Press any key to close this window.
    pause
    exit /b %errorlevel%
) 