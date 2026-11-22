@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."
title EnglishCentral Studio - Conector real do Chrome (Windows)
set "ROOT=%CD%"
set "RUNTIME=%ROOT%\runtime"
set "APP=%RUNTIME%\EnglishCentral-Studio"
set "SOURCE_ZIP=%ROOT%\EnglishCentral-Studio-18.13.3-G0DMOD3.zip"

echo.
echo ============================================================
echo   ENGLISHCENTRAL STUDIO - CHROME REAL DO WINDOWS
echo ============================================================
echo.
if not exist "%SOURCE_ZIP%" (
  echo ERRO: o arquivo original EnglishCentral-Studio-18.13.3-G0DMOD3.zip nao foi encontrado.
  echo Extraia o pacote completo antes de executar este arquivo.
  pause
  exit /b 1
)

py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3 nao foi encontrado.
  echo Instale Python 3.10 ou superior em https://www.python.org/downloads/windows/
  echo Durante a instalacao, marque "Add Python to PATH" e instale o Python Launcher.
  pause
  exit /b 1
)

if not exist "%APP%\servidor.py" (
  echo [1/3] Extraindo o projeto original V18.13.3...
  if not exist "%RUNTIME%" mkdir "%RUNTIME%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%SOURCE_ZIP%' -DestinationPath '%RUNTIME%' -Force"
  if errorlevel 1 (
    echo Falha ao extrair o projeto original.
    pause
    exit /b 1
  )
)

echo [2/3] Aplicando e validando a ponte local...
py -3 "%ROOT%\install_windows_bridge.py" "%APP%"
if errorlevel 1 (
  echo.
  echo ERRO: a ponte nao foi aplicada. Nenhuma conexao simulada sera usada.
  pause
  exit /b 1
)

cd /d "%APP%"
set "EC_FORCE_DESKTOP=1"
set "EC_PC_BRIDGE=1"
set "EC_LOCAL_PANEL_ORIGIN=https://englishcentral-studio.onrender.com"
set "EC_PORT=8765"
set "EC_REMOTE_MODE="
set "EC_PUBLIC_URL="
set "EC_PUBLIC_SESSIONS="
set "EC_PUBLIC_SESSION_SECRET="
set "EC_PANEL_TOKEN="
set "EC_TERMUX="
set "EC_TRUSTED_PROXY_IPS="

echo.
echo [3/3] Iniciando o servidor local que controla o Chrome existente...
echo Endereco local: http://127.0.0.1:8765
echo Cookies e login permanecem no Chrome deste computador.
echo Mantenha esta janela aberta enquanto utilizar a automacao.
echo.
py -3 iniciar.py
if errorlevel 1 (
  echo.
  echo O conector terminou com erro. Veja a mensagem acima.
  pause
)
endlocal
