Set WshShell = CreateObject("WScript.Shell")

' 1. Asegurar inicio de WSL2, esperar al demonio de Docker y levantar contenedores
WshShell.Run "wsl.exe -d Ubuntu bash -c ""cd /mnt/c/Users/MaxRo/OneDrive/Escritorio/GTOPagos_Back && for i in {1..30}; do docker info > /dev/null 2>&1 && break || sleep 1; done; docker compose up -d""", 0, True

' 2. Esperar a que la red y servicios levanten
WScript.Sleep 2000

' 3. Limpiar cualquier proxy residual previo en puerto 1450
WshShell.Run "cmd.exe /c for /f ""tokens=5"" %a in ('netstat -ano ^| findstr :1450 ^| findstr LISTENING') do taskkill /F /PID %a", 0, True
WScript.Sleep 1000

' 4. Iniciar el proxy TCP silenciosamente en segundo plano
WshShell.Run "cmd.exe /c """"C:\Program Files\nodejs\node.exe"" ""C:\Users\MaxRo\OneDrive\Escritorio\GTOPagos_Back\scripts\wsl_port_proxy.js"" > ""C:\Users\MaxRo\OneDrive\Escritorio\GTOPagos_Back\scripts\proxy.log"" 2>&1""", 0, False
WScript.Sleep 1500