@echo off
echo Deteniendo proxy y backend de GTOPagos...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :1450 ^| findstr LISTENING') do taskkill /F /PID %%a 2>nul
wsl.exe -d Ubuntu docker compose -f /mnt/c/Users/MaxRo/OneDrive/Escritorio/GTOPagos_Back/docker-compose.yml down
echo Backend y proxy detenidos exitosamente.
pause