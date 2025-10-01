@echo off
setlocal EnableDelayedExpansion

:: Set script variables
set PROJECT_DIR=%~dp0..
set LOG_FILE=C:\temp\smartbet_sync.log
set DATE_FORMAT=%date% %time%

:: Navigate to project directory
cd /d "%PROJECT_DIR%" || (
    echo Failed to navigate to project directory
    exit /b 1
)

:: Log start of execution
echo [%DATE_FORMAT%] Starting SmartBet data sync... >> "%LOG_FILE%"

:: Check for virtual environment and activate
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
) else (
    echo [%DATE_FORMAT%] No virtual environment found. Proceeding without activation. >> "%LOG_FILE%"
)

:: Run the sync command and capture output
python manage.py sync_realtime_data --leagues 274 332 > temp_output.txt 2>&1
set /p OUTPUT=<temp_output.txt

:: Parse output for statistics (simplified in batch)
set MATCHES_CREATED=0
set MATCHES_UPDATED=0
set ODDS_STORED=0

for /f "tokens=*" %%a in ('findstr /r "fixtures created" temp_output.txt') do (
    for /f "tokens=1 delims= " %%b in ("%%a") do set MATCHES_CREATED=%%b
)

for /f "tokens=*" %%a in ('findstr /r "fixtures updated" temp_output.txt') do (
    for /f "tokens=1 delims= " %%b in ("%%a") do set MATCHES_UPDATED=%%b
)

for /f "tokens=*" %%a in ('findstr /r "odds snapshots stored" temp_output.txt') do (
    for /f "tokens=1 delims= " %%b in ("%%a") do set ODDS_STORED=%%b
)

:: Log command output
type temp_output.txt >> "%LOG_FILE%"
del temp_output.txt

:: Add summary log line
echo [✓] SmartBet sync completed at %DATE_FORMAT% – Matches: %MATCHES_UPDATED% updated, %MATCHES_CREATED% created, Odds: %ODDS_STORED% matched >> "%LOG_FILE%"
echo. >> "%LOG_FILE%"

:: If we activated a virtual environment, deactivate it
if defined VIRTUAL_ENV (
    call deactivate
)

endlocal 