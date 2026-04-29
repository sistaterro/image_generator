@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "BASE_DIR=%~dp0"
set "COMFY_DIR=%BASE_DIR%comfy_server\ComfyUI"
set "COMFY_PORT=8188"
set "COMFY_EXPOSED_IP="
set "MAX_ATTEMPTS=90"

if not exist "%COMFY_DIR%\main.py" (
    echo ERROR: ComfyUI was not found at "%COMFY_DIR%"
    exit /b 1
)

for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$ip = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254*' -and $_.PrefixOrigin -ne 'WellKnown' } | Select-Object -First 1 -ExpandProperty IPAddress; if ($ip) { $ip } else { '127.0.0.1' }"`) do set "COMFY_EXPOSED_IP=%%I"
if not defined COMFY_EXPOSED_IP set "COMFY_EXPOSED_IP=127.0.0.1"

echo Starting ComfyUI at %COMFY_EXPOSED_IP%:%COMFY_PORT%...
start "ComfyUI" /D "%COMFY_DIR%" cmd /k "call env\Scripts\activate.bat && python main.py --listen 0.0.0.0 --port %COMFY_PORT%"

echo Waiting for ComfyUI at http://%COMFY_EXPOSED_IP%:%COMFY_PORT%/system_stats
for /l %%N in (1,1,%MAX_ATTEMPTS%) do (
    powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 -Uri 'http://%COMFY_EXPOSED_IP%:%COMFY_PORT%/system_stats'; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }" >nul 2>&1
    if !errorlevel! equ 0 goto comfy_ready
    timeout /t 1 /nobreak >nul
)

echo ERROR: ComfyUI did not become available at http://%COMFY_EXPOSED_IP%:%COMFY_PORT%
exit /b 1

:comfy_ready
echo ComfyUI is ready.

cd /d "%BASE_DIR%"
call env\Scripts\activate.bat
python main.py

pause
