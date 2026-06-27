@echo off
echo ====================================
echo Email Scraper - Starting Services
echo ====================================
echo.

echo Starting FastAPI backend on port 8000...
start "FastAPI Backend" cmd /k "python server.py"
timeout /t 3 /nobreak >nul

echo Starting Flask frontend on port 5000...
start "Flask Frontend" cmd /k "python app.py"
timeout /t 2 /nobreak >nul

echo.
echo ====================================
echo Services Started!
echo ====================================
echo.
echo Backend API: http://localhost:8000
echo Frontend UI: http://localhost:5000
echo.
echo Press Ctrl+C in each window to stop
echo ====================================
