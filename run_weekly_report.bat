@echo off
cd /d "%~dp0"
"C:\Users\Paulo\AppData\Local\Python\pythoncore-3.14-64\python.exe" weekly_report.py
exit /b %ERRORLEVEL%

