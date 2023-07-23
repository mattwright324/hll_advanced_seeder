@echo off

schtasks /query /tn "HLLAdvSeeder" /fo LIST 

ECHO:
if not ERRORLEVEL 1 (
ECHO The task is verified and should be displayed above.
ECHO If the time is incorrect, run setup.bat again.
ECHO To test the script, run runGame.bat
)
if ERRORLEVEL 1 (
ECHO:
ECHO There is no scheduled task present, run setup.bat to install.
)

PAUSE