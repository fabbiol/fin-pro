@echo off
chcp 65001 >nul
title Fin Pro - versoes
cd /d "%~dp0"
rem Sem argumentos: mostra a versao atual e o que mudou. Exemplos:
rem   versoes.bat listar
rem   versoes.bat nova "Titulo da versao" -m "o que mudou"
rem   versoes.bat voltar v1.8.0
".venv\Scripts\python.exe" ferramentas\versao.py %*
echo.
pause
