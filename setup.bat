@echo off
setlocal enableDelayedExpansion

for /f "delims=" %%x in (config.txt) do (set "%%x")
set "workDir=%cd%"

REM Removing previous scheduled task instance if it exists.
REM schtasks /delete /tn "HLL-Seeder" /f >NUL 2>&1
schtasks /delete /tn "HLLAdvSeeder" /f >nul2>nul
if not ERRORLEVEL 1 (
echo Succesfully removed previous scheduled task. Please continue to setup completely.
)
if ERRORLEVEL 1 (
echo No previously scheduled task to remove. Please continue to setup completely.
)



ECHO:

ECHO Enter the time you would like the script to start every morning.
ECHO For example if are targeting 10AM Eastern Time, enter 10:00:00. If you are in Pacific time, enter 7:00:00.
ECHO:
set /p startupTime="Enter Time: "

ECHO:

REM editing XML file to add local directory. Had to add a repl library because batch doesn't support stuff natively. 
type "TaskSchedulerTemplate.xml"|repl "workDir" "%workDir%"|repl "startTime" "%startupTime%" >TaskSchedulerTemplate_local.xml

schtasks /create /xml "%workDir%\TaskSchedulerTemplate_Local.xml" /tn "HLLAdvSeeder"

ECHO:
if not ERRORLEVEL 1 (
ECHO Setup Complete. A scheduled task is created on your computer to run runGame.bat every day at %startupTime%.
)
if ERRORLEVEL 1 (
ECHO:
ECHO There was an error while creating the scheduled task. Please make sure your startup time is formatted correctly.
PAUSE
EXIT 
)

ECHO:
ECHO To test the script at any time, run runGame.bat.
ECHO To remove the scheduled task from your system, run uninstall.bat
ECHO To verify the scheduled task, run verify.bat.

PAUSE