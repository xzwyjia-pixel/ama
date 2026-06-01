@echo off
chcp 65001 >nul
title AMA - Agent Management Agent v1.0
cd /d "%~dp0"

echo.
echo ============================================
echo   AMA - Agent Management Agent v1.0
echo ============================================
echo.
echo [1] Full pipeline: scan + seed + start server
echo [2] Scan agents only (update inventory)
echo [3] Start Store Server (background daemon)
echo [4] Stop Store Server
echo [5] Server Status
echo [6] Open Store in browser
echo [7] Open Cost Calculator in browser
echo [8] Install as Windows startup service
echo [9] View todays logs
echo.
echo ============================================

if "%1"=="" (
    set /p choice="Select option (1-9): "
) else (
    set choice=%1
)

if "%choice%"=="1" goto full
if "%choice%"=="2" goto scan
if "%choice%"=="3" goto start-srv
if "%choice%"=="4" goto stop-srv
if "%choice%"=="5" goto status
if "%choice%"=="6" goto open-store
if "%choice%"=="7" goto open-calc
if "%choice%"=="8" goto install-service
if "%choice%"=="9" goto view-logs
goto end

:full
echo.
echo =============================================
echo   Full Pipeline: Scan + Seed + Start
echo =============================================
echo.
echo [1/3] Scanning all agents...
python3 scripts\ama-scan.py
if errorlevel 1 (
    echo ERROR: Scan failed
    goto end
)
echo.
echo [2/3] Seeding database and starting server...
python3 scripts\ama-server-prod.py --daemon
echo.
echo [3/3] Opening Store in browser...
timeout /t 3 /nobreak >nul
start http://localhost:8765/store
echo.
echo =============================================
echo   AMA is now LIVE!
echo   Store: http://localhost:8765/store
echo   Calc:  http://localhost:8765/calculator
echo   API:   http://localhost:8765/api/agents
echo =============================================
goto end

:scan
echo.
echo Running agent inventory scan...
python3 scripts\ama-scan.py
python3 scripts\ama-report.py
echo.
echo Done. Report in data\agent-inventory-report-latest.md
goto end

:start-srv
echo.
echo Starting AMA Store Server as background daemon...
python3 scripts\ama-server-prod.py --daemon
goto end

:stop-srv
echo.
echo Stopping AMA Store Server...
python3 scripts\ama-server-prod.py --stop
goto end

:status
python3 scripts\ama-server-prod.py --status
goto end

:open-store
start http://localhost:8765/store
echo Opening Store in browser...
goto end

:open-calc
start http://localhost:8765/calculator
echo Opening Cost Calculator in browser...
goto end

:install-service
echo.
echo =============================================
echo   Install AMA as Windows Startup Task
echo =============================================
echo.
set TASK_NAME=AMA-Agent-Store
set BAT_PATH=%~dp0start-ama.bat

echo Creating scheduled task: %TASK_NAME%
echo This will auto-start AMA when you log in.
echo.

schtasks /create /tn "%TASK_NAME%" /tr "%BAT_PATH% 3" /sc onlogon /delay 0001:00 /f /rl highest
if errorlevel 1 (
    echo.
    echo ERROR: Failed to create scheduled task.
    echo Try running this script as Administrator.
) else (
    echo.
    echo SUCCESS! AMA will auto-start on login.
    echo   Task: %TASK_NAME%
    echo   Run: schtasks /run /tn "%TASK_NAME%" to start now
    echo   Run: schtasks /delete /tn "%TASK_NAME%" /f to remove
)
goto end

:view-logs
echo.
echo Today's server logs:
echo =============================================
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do set TODAY=%%c%%a%%b
if exist logs\ama-server-%TODAY%.log (
    type logs\ama-server-%TODAY%.log
) else (
    echo No logs found for today.
    echo Available logs:
    dir /b logs\ 2>nul || echo   (no logs directory)
)
goto end

:end
echo.
