@echo off

schtasks /delete /tn "HLLAdvSeeder"

ECHO "Scheduled task succesfully removed."

PAUSE