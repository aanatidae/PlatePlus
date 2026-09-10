@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start_plateplus_demo.ps1"
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo.
  echo [PlatePlus] Demo startup stopped. Review the message above; this window will remain open.
  pause
)
exit /b %RESULT%
