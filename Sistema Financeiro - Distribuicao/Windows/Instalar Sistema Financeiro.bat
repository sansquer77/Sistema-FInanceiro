@echo off
setlocal

set "PACKAGE_DIR=%~dp0"
set "SOURCE_DIR=%PACKAGE_DIR%Aplicativo"
set "DEST_DIR=%USERPROFILE%\Documents\Sistema Financeiro"
set "LAUNCHER_PATH=%DEST_DIR%\Abrir Sistema Financeiro.bat"
set "ICON_PATH=%DEST_DIR%\web\assets\app-icon.ico"
set "PYTHON_CHECK="

echo Instalando Sistema Financeiro para Windows...
echo.

if not exist "%SOURCE_DIR%" (
  echo Erro: pasta Aplicativo nao encontrada ao lado do instalador.
  echo.
  pause
  exit /b 1
)

where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CHECK=py -3"
  py -3 --version >nul 2>nul
  if errorlevel 1 set "PYTHON_CHECK="
)

if not defined PYTHON_CHECK (
  where python >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_CHECK=python"
    python --version >nul 2>nul
    if errorlevel 1 set "PYTHON_CHECK="
  )
)

if not defined PYTHON_CHECK (
  echo Aviso: Python 3 nao encontrado no PATH.
  echo.
  echo O app precisa do Python 3 instalado para abrir.
  echo Instale em https://www.python.org/downloads/windows/
  echo Marque a opcao "Add python.exe to PATH" durante a instalacao.
  echo.
)

if not exist "%DEST_DIR%" mkdir "%DEST_DIR%"

echo Copiando arquivos do sistema para:
echo %DEST_DIR%
echo.

robocopy "%SOURCE_DIR%" "%DEST_DIR%" /E /XD data tests docs __pycache__ ".git" "Sistema Financeiro.app" /XF ".DS_Store" "._*" "*.pyc" "server.log" >nul
if %errorlevel% GEQ 8 (
  echo Erro ao copiar os arquivos do sistema.
  echo.
  pause
  exit /b 1
)

echo Criando icone na Area de Trabalho...
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop = [Environment]::GetFolderPath('Desktop'); $shortcutPath = Join-Path $desktop 'Sistema Financeiro.lnk'; $shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($shortcutPath); $shortcut.TargetPath = $env:LAUNCHER_PATH; $shortcut.WorkingDirectory = $env:DEST_DIR; $shortcut.Description = 'Abrir Sistema Financeiro'; if (Test-Path $env:ICON_PATH) { $shortcut.IconLocation = $env:ICON_PATH }; $shortcut.Save()"
if not %errorlevel%==0 (
  echo Aviso: nao foi possivel criar o icone automaticamente.
  echo Voce ainda pode abrir o app por:
  echo %LAUNCHER_PATH%
  echo.
)

echo Instalacao concluida.
echo.
echo Abra o app pelo icone "Sistema Financeiro" na Area de Trabalho.
echo.
echo O banco de dados sera criado vazio no primeiro uso em:
echo %DEST_DIR%\data\finance.db
echo.
pause
exit /b 0
