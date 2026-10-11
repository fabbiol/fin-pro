@echo off
chcp 65001 >nul
title Restaurar o Fin Pro
echo.
echo  RESTAURAR O FIN PRO A PARTIR DESTE BACKUP
echo  -----------------------------------------
echo  Copia o codigo, os bancos de dados, os arquivos e as configuracoes
echo  para uma pasta nova. Nada e apagado deste backup.
echo.
set "DESTINO=%USERPROFILE%\Documents\Fin Pro"
set /p "DESTINO=Onde o sistema vai ficar (ENTER = %DESTINO%): "
echo.
py -3 "%~dp0restaurar_backup.py" "%~dp0." "%DESTINO%"
if errorlevel 9009 python "%~dp0restaurar_backup.py" "%~dp0." "%DESTINO%"
echo.
pause
