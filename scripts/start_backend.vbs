Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wsl.exe -d Ubuntu docker compose -f /mnt/c/Users/MaxRo/OneDrive/Escritorio/GTOPagos_Back/docker-compose.yml up -d", 0, False