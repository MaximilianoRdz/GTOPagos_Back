@echo off
title GTOPagos - Servidor Backend
echo ====================================================
echo  Iniciando Servidor GTOPagos (Docker + Proxy 1450)
echo ====================================================
echo.
echo 1. Levantando base de datos y backend en Docker...
wsl.exe -d Ubuntu bash -c "cd /mnt/c/Users/MaxRo/OneDrive/Escritorio/GTOPagos_Back && docker compose up -d"
echo.
echo 2. Limpiando procesos previos en puerto 1450...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :1450 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
echo.
echo [OK] Backend activo y conectado a https://gtopagos.maxrdzs.com
echo [INFO] Manten esta ventana abierta (o minimizada) mientras uses el sistema.
echo.
"C:\Program Files\nodejs\node.exe" "%~dp0scripts\wsl_port_proxy.js"
pause
