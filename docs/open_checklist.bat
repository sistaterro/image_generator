@echo off
setlocal

set "CHECKLIST=%~dp0checklist.html"

if not exist "%CHECKLIST%" (
  echo Could not find checklist.html next to this script.
  pause
  exit /b 1
)

start "" "%CHECKLIST%"
