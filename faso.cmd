@echo off
rem Lanceur sans blocage PowerShell : faso.cmd demarrer | arreter | etat | revoquer 402917M | reintegrer 402917M
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0faso.ps1" %*
