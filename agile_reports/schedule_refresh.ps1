# Jira Connector Automation Script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
cd $ScriptDir

Write-Host "Starting Jira Connector Agent..." -ForegroundColor Cyan

# Run the agent
python agent.py

if ($LASTEXITCODE -eq 0) {
    Write-Host "Jira data refresh successful." -ForegroundColor Green
} else {
    Write-Host "Jira data refresh failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

# Optional: Trigger Power BI Refresh via API if configured
# This requires a Power BI App Registration and Service Principal
# For now, we assume Power BI Desktop or Service is watching the Excel file.
