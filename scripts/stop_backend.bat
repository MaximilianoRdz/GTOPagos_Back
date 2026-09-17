@echo off
echo Deteniendo backend de GTOPagos...
wsl.exe -d Ubuntu docker compose -f /mnt/c/Users/MaxRo/OneDrive/Escritorio/GTOPagos_Back/docker-compose.yml down
echo Backend detenido exitosamente.
pause