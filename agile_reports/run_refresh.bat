@echo off
echo ========================================
echo 🎯 Jira Intelligence Agent - Full Refresh
echo ========================================
echo.

echo [1/3] Refreshing Project M5R...
python agent.py --project M5R --force

echo.
echo [2/3] Refreshing Project MFS5T...
python agent.py --project MFS5T --force

echo.
echo [3/3] Refreshing Project PDB...
python agent.py --project PDB --force

echo.
echo ========================================
echo ✅ Refresh Complete! All Workbooks Updated.
echo ========================================
pause
