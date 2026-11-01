@echo off
rem Code a usage unique : code.cmd 318264B
docker run --rm -v "%~dp0demo:/demo:ro" python:3.12-slim python /demo/code.py %1
