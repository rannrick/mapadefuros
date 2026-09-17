@echo off
chcp 65001 >nul
REM ================================================================
REM  Gera dist\MapaDeFuros\MapaDeFuros.exe e o instalador
REM  dist_instalador\MapaDeFuros_Setup_1.0.0.exe
REM  Requisitos: Python 3.10+ (python.org, com Tcl/Tk) e Inno Setup 6
REM ================================================================
cd /d "%~dp0"

where python >nul 2>nul || (echo [ERRO] Python nao encontrado. Instale em python.org & pause & exit /b 1)

echo [1/4] Criando ambiente virtual...
if not exist .venv python -m venv .venv
call .venv\Scripts\activate.bat

echo [2/4] Instalando dependencias...
python -m pip install --upgrade pip >nul
pip install -r requirements.txt || goto erro

echo [3/4] Empacotando com PyInstaller...
pyinstaller MapaDeFuros.spec --noconfirm --clean || goto erro

echo [4/4] Gerando instalador com Inno Setup...
set ISCC="%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist %ISCC% set ISCC="%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if not exist %ISCC% (
  echo [AVISO] Inno Setup 6 nao encontrado - baixe em https://jrsoftware.org/isdl.php
  echo         O programa portatil ja esta em dist\MapaDeFuros\MapaDeFuros.exe
  pause & exit /b 0
)
%ISCC% installer\MapaDeFuros.iss || goto erro

echo.
echo  PRONTO!  Instalador: dist_instalador\MapaDeFuros_Setup_1.0.0.exe
explorer dist_instalador
pause
exit /b 0

:erro
echo [ERRO] Falha na compilacao.
pause
exit /b 1
