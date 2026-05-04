@echo off
TITLE GestVoice Smart Assistant
COLOR 0A

echo ========================================================
echo        STARTING GESTVOICE SMART ASSISTANT...
echo ========================================================
echo.
echo Please wait while the AI components load. This may take a few seconds...
echo.

REM 1. Navigate to correct directory explicitly
cd /d "d:\ishita"

REM 2. Run main script reliably
python new.py

REM 3. Ensure no silent failure
echo.
echo ========================================================
echo  [SYSTEM] GestVoice stopped. 
echo ========================================================
pause
