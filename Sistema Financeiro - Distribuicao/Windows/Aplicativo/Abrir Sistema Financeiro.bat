@echo off
setlocal

set "APP_DIR=%~dp0"
set "APP_HOST=127.0.0.1"
set "APP_PORT=8010"
set "APP_URL=http://127.0.0.1:%APP_PORT%"
set "PYTHON_CMD="

where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
  py -3 --version >nul 2>nul
  if errorlevel 1 set "PYTHON_CMD="
)

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_CMD=python"
    python --version >nul 2>nul
    if errorlevel 1 set "PYTHON_CMD="
  )
)

if not defined PYTHON_CMD (
  echo Python 3 nao encontrado.
  echo.
  echo Instale o Python 3 em https://www.python.org/downloads/windows/
  echo Marque a opcao "Add python.exe to PATH" durante a instalacao.
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri $env:APP_URL -TimeoutSec 1; if ($response.StatusCode -ge 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
if not %errorlevel%==0 (
  if not exist "%APP_DIR%data" mkdir "%APP_DIR%data"
  start "Sistema Financeiro Servidor" /D "%APP_DIR%" /min cmd /c "set APP_HOST=%APP_HOST%&& set APP_PORT=%APP_PORT%&& set APP_URL=%APP_URL%&& %PYTHON_CMD% app.py >> data\server.log 2>&1"

  for /l %%i in (1,1,40) do (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "try { $response = Invoke-WebRequest -UseBasicParsing -Uri $env:APP_URL -TimeoutSec 1; if ($response.StatusCode -ge 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>nul
    if not errorlevel 1 goto open_app
    timeout /t 1 /nobreak >nul
  )
)

:open_app
start "" "%APP_URL%"
exit /b 0
