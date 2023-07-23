@echo off

for /f "delims=" %%x in (config.txt) do (set "%%x")

start cmd.exe /c "python %~dp0\seeding.py"

ECHO "Game will automatically close in %closeGameAfterMinutes% minutes from this message"
ECHO "Close this window to cancel the process"
set /A timeout =  %closeGameAfterMinutes%*60
timeout /t %timeout% /nobreak

rem Kill HLL
TASKKILL /IM HLL-Win64-Shipping.exe /F

exit
