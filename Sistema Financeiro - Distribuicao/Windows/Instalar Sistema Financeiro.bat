@echo off
setlocal

set "PACKAGE_DIR=%~dp0"
set "SOURCE_DIR=%PACKAGE_DIR%Aplicativo"
set "DEST_DIR=%USERPROFILE%\Documents\Sistema Financeiro"
set "LAUNCHER_PATH=%DEST_DIR%\Abrir Sistema Financeiro.bat"
set "LAN_LAUNCHER_PATH=%DEST_DIR%\Abrir Sistema Financeiro na Rede.bat"
set "ICON_PATH=%DEST_DIR%\SistemaFinanceiro\SistemaFinanceiro.exe"

echo Instalando Sistema Financeiro para Windows...
echo.

if not exist "%SOURCE_DIR%" (
  echo Erro: pasta Aplicativo nao encontrada ao lado do instalador.
  echo.
  pause
  exit /b 1
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

powershell -NoProfile -ExecutionPolicy Bypass -Command "$desktop = [Environment]::GetFolderPath('Desktop'); $shortcutPath = Join-Path $desktop 'Sistema Financeiro Rede.lnk'; $shell = New-Object -ComObject WScript.Shell; $shortcut = $shell.CreateShortcut($shortcutPath); $shortcut.TargetPath = $env:LAN_LAUNCHER_PATH; $shortcut.WorkingDirectory = $env:DEST_DIR; $shortcut.Description = 'Abrir Sistema Financeiro na rede local'; if (Test-Path $env:ICON_PATH) { $shortcut.IconLocation = $env:ICON_PATH }; $shortcut.Save()"
if not %errorlevel%==0 (
  echo Aviso: nao foi possivel criar o icone de rede automaticamente.
  echo Voce ainda pode abrir o modo rede por:
  echo %LAN_LAUNCHER_PATH%
  echo.
)

echo Instalacao concluida.
echo.
echo Abra o app pelo icone "Sistema Financeiro" na Area de Trabalho.
echo Para acessar de outros computadores na mesma rede, use "Sistema Financeiro Rede".
echo.
echo O banco de dados sera criado vazio no primeiro uso em:
echo %DEST_DIR%\data\finance.db
echo.
pause
exit /b 0
