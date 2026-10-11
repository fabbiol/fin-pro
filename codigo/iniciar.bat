@echo off
chcp 65001 >nul
title Fin Pro
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Criando ambiente Python - somente na primeira vez...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo.
        echo Python 3.10 ou superior nao encontrado. Instale em https://www.python.org/downloads/
        pause
        exit /b 1
    )
)

".venv\Scripts\python.exe" -c "import fastapi, openpyxl, pypdfium2, zxingcpp, rapidocr, rapidocr_onnxruntime, anthropic, segno, webview, pystray, xlrd, reportlab" 2>nul
if errorlevel 1 (
    echo Instalando dependencias - pode levar alguns minutos na primeira vez...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo Falha ao instalar as dependencias. Verifique sua conexao com a internet.
        pause
        exit /b 1
    )
    echo Preparando o OCR - baixa os modelos de leitura uma unica vez...
    ".venv\Scripts\python.exe" -c "from app.boleto.ocr import motor_ocr; motor_ocr.carregar(); print('OCR pronto:', motor_ocr.modelo)"
)

rem Abre o aplicativo (janela propria + icone na bandeja) sem deixar a janela preta aberta
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" -m app
) else (
    ".venv\Scripts\python.exe" -m app
    pause
)
