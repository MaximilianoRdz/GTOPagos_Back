@echo off
echo Generando respaldo de base de datos GTOPagos...
wsl.exe -d Ubuntu bash -c "/mnt/c/Users/MaxRo/OneDrive/Escritorio/GTOPagos_Back/scripts/backup_db.sh"
pause