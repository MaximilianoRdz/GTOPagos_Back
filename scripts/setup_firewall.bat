@echo off
echo ===================================================
echo   Configurando Regla de Seguridad del Firewall
echo   Puerto 1450 (Proxy Local GTOPagos)
echo ===================================================
echo.

net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Este script requiere permisos de Administrador.
    echo Por favor haz clic derecho sobre este archivo y selecciona "Ejecutar como administrador".
    echo.
    pause
    exit /b 1
)

netsh advfirewall firewall delete rule name="GTOPagos Proxy 1450" >nul 2>&1
netsh advfirewall firewall add rule name="GTOPagos Proxy 1450" dir=in action=allow protocol=TCP localport=1450 profile=private,public

echo.
echo [EXITO] Regla de firewall para el puerto 1450 configurada exitosamente.
echo El puerto necesario para GTOPagos esta habilitado con proteccion activa.
echo.
pause
