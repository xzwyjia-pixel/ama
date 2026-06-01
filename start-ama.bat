@echo off
chcp 65001 >nul
title AMA - Agent Management Agent

echo.
echo ============================================
echo   AMA - Agent Management Agent v1.0
echo ============================================
echo.
echo [1] Scan all agents -> generate inventory
echo [2] Generate report from inventory
echo [3] Start Agent Store (http://localhost:8765)
echo [4] Open Cost Calculator in browser
echo [5] Full pipeline: scan + report + store
echo.
echo ============================================

if "%1"=="" (
    set /p choice="Select option (1-5): "
) else (
    set choice=%1
)

if "%choice%"=="1" goto scan
if "%choice%"=="2" goto report
if "%choice%"=="3" goto store
if "%choice%"=="4" goto calc
if "%choice%"=="5" goto all
goto end

:scan
echo.
echo Running agent scanner...
python3 scripts/ama-scan.py
goto end

:report
echo.
echo Generating report...
python3 scripts/ama-report.py
echo.
echo Report generated in output/ folder
goto end

:store
echo.
echo Starting AMA Agent Store...
echo Store: http://localhost:8765/store
echo Calc:  http://localhost:8765/calculator
echo API:   http://localhost:8765/api/agents
echo.
start http://localhost:8765/store
python3 scripts/ama-store-server.py
goto end

:calc
echo.
echo Opening AI Cost Calculator...
start "" "public\index.html"
goto end

:all
echo.
echo Running full pipeline...
echo.
echo [1/3] Scanning agents...
python3 scripts/ama-scan.py
echo.
echo [2/3] Generating report...
python3 scripts/ama-report.py
echo.
echo [3/3] Starting Agent Store...
start http://localhost:8765/store
python3 scripts/ama-store-server.py
goto end

:end
