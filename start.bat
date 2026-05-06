@echo off
echo ========================================
echo   RAG Scanner - Quick Start
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Create virtual environment if not exists
if not exist "venv" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Install dependencies
echo [2/3] Installing dependencies...
pip install -r requirements.txt --quiet

REM Start server
echo [3/3] Starting server...
echo.
echo ========================================
echo   Server running at: http://localhost:5000
echo   Press Ctrl+C to stop
echo ========================================
echo.

python main.py

pause