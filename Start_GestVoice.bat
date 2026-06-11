@echo off
TITLE GestVoice Smart Assistant
COLOR 0A

echo ========================================================
echo        STARTING GESTVOICE SMART ASSISTANT...
echo ========================================================
echo.
echo Please wait while the AI components load. This may take a few seconds...
echo.

REM 1. Start MongoDB Backend
python setup_mongo.py

REM 2. Run unified launcher (starts Django + AI + opens dashboard)
python launcher.py

REM 3. Ensure no silent failure
echo.
echo ========================================================
echo  [SYSTEM] GestVoice stopped. 
echo ========================================================
pause
