Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "wsl.exe -d Ubuntu docker compose -f /mnt/c/Users/MaxRo/OneDrive/Escritorio/GTOPagos_Back/docker-compose.yml up -d", 0, True
WshShell.Run "cmd.exe /c node ""C:\Users\MaxRo\OneDrive\Escritorio\GTOPagos_Back\scripts\wsl_port_proxy.js""", 0, False