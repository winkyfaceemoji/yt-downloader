@echo off
rem Data hub launcher: hub.cmd status | log | run capture --url <url> --mode audio^|video^|both [--music]
rem Calls siblings by full path (%~dp0); no prompts, no pause; the exit code is the result.
"%~dp0.venv\Scripts\python.exe" "%~dp0main.py" %*
exit /b %errorlevel%
