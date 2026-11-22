@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0\.."
title EnglishCentral Studio - Conector real do Chrome (Windows)
set "REPO_ROOT=%CD%"
set "RUNTIME=%REPO_ROOT%\runtime"
set "APP=%RUNTIME%\EnglishCentral-Studio"
set "ARCHIVE=%REPO_ROOT%\EnglishCentral-Studio-18.13.3-G0DMOD3.zip"

echo.
echo ============================================================
echo   ENGLISHCENTRAL STUDIO - CONECTOR REAL DO CHROME NO WINDOWS
echo ============================================================
echo.
if not exist "%ARCHIVE%" (
  echo ERRO: nao encontrei o arquivo original EnglishCentral Studio.
  echo Extraia o ZIP completo do repositorio antes de executar este BAT.
  pause
  exit /b 1
)
if not exist "%APP%\servidor.py" (
  echo Extraindo o codigo original V18.13.3...
  if not exist "%RUNTIME%" mkdir "%RUNTIME%"
  powershell -NoProfile -ExecutionPolicy Bypass -Command "Expand-Archive -LiteralPath '%ARCHIVE%' -DestinationPath '%RUNTIME%' -Force"
  if errorlevel 1 (
    echo Falha ao extrair o projeto original.
    pause
    exit /b 1
  )
)
py -3 --version >nul 2>&1
if errorlevel 1 (
  echo Python 3.10 ou superior nao foi encontrado.
  echo Instale em https://www.python.org/downloads/windows/ e marque Add Python to PATH.
  pause
  exit /b 1
)
echo Aplicando a ponte local ao codigo original...
py -3 "%REPO_ROOT%\windows\apply_pc_bridge.py" "%APP%"
if errorlevel 1 (
  echo A atualizacao da ponte falhou. Nenhuma simulacao sera usada.
  pause
  exit /b 1
)
cd /d "%APP%"
set "EC_FORCE_DESKTOP=1"
set "EC_PC_BRIDGE=1"
set "EC_LOCAL_PANEL_ORIGIN=https://englishcentral-studio.onrender.com"
set "EC_PORT=8765"
set "EC_REMOTE_MODE="
set "EC_PUBLIC_SESSIONS="
set "EC_PUBLIC_SESSION_ID="
set "EC_PANEL_TOKEN="
echo.
echo Conector local iniciando em 127.0.0.1:8765.
echo O login e os cookies permanecem neste computador.
echo Mantenha esta janela aberta enquanto a automacao estiver ativa.
echo.
py -3 iniciar.py
if errorlevel 1 (
  echo.
  echo O conector encerrou com erro. Confira a mensagem acima.
  pause
)
endlocal
