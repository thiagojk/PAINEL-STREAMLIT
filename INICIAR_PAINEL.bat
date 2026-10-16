@echo off
setlocal
cd /d "%~dp0"
py -3 --version >nul 2>&1
if not errorlevel 1 (
    set "PQAVS_PY=py -3"
) else (
    python --version >nul 2>&1
    if errorlevel 1 (
        echo Instale o Python 3.12 ou superior em https://www.python.org/downloads/
        echo Marque a opcao de adicionar Python ao PATH.
        pause
        exit /b 1
    )
    set "PQAVS_PY=python"
)
%PQAVS_PY% -c "import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)"
if errorlevel 1 (
    echo Este painel requer Python 3.12 ou superior. Versao validada: 3.12.
    pause
    exit /b 1
)
if not exist ".venv\Scripts\python.exe" (
    %PQAVS_PY% -m venv .venv
    if errorlevel 1 goto :falha
)
".venv\Scripts\python.exe" scripts\iniciar_local.py
if errorlevel 1 goto :falha
exit /b 0
:falha
echo Nao foi possivel iniciar. Verifique a conexao e as mensagens acima.
pause
exit /b 1
