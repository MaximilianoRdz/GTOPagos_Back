Set objShell = CreateObject("Shell.Application")
objShell.ShellExecute "cmd.exe", "/c """ & "c:\Users\MaxRo\OneDrive\Escritorio\GTOPagos_Back\scripts\setup_firewall.bat" & """", "", "runas", 1
