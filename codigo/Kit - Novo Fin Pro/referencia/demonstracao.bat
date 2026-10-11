@echo off
chcp 65001 >nul
title Fin Pro - Demonstracao
cd /d "%~dp0"

rem Versao de demonstracao: dados de exemplo em "dados_demo", porta 8010 e nada e enviado para fora.
rem Pode ficar aberta junto com o sistema de verdade (que usa a porta 8000).
rem Para montar os dados de novo do zero:  demonstracao.bat --refazer

if not exist ".venv\Scripts\python.exe" (
    echo Ambiente Python nao encontrado. Rode primeiro o iniciar.bat.
    pause
    exit /b 1
)

if exist ".venv\Scripts\pythonw.exe" (
    ".venv\Scripts\python.exe" -m app.demonstracao --dados %*
    if errorlevel 1 (
        echo.
        echo Falha ao preparar os dados de demonstracao.
        pause
        exit /b 1
    )
    start "" ".venv\Scripts\pythonw.exe" -m app.demonstracao
) else (
    ".venv\Scripts\python.exe" -m app.demonstracao %*
    pause
)
