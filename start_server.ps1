# Navigate to the server directory
Set-Location -Path ".\hindsight_server"

# Start the Python backend script in the background
$PythonJob = Start-Job -ScriptBlock { python server_backend.py }

# Start the uwsgi server script
Start-Process "python" -ArgumentList "run_server.py"

# Register a block of code to run when the script exits
# This traps the exiting of the PowerShell script and ensures cleanup
$global:exitEvent = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -SupportEvent -Action {
    Write-Host "Cleaning up..."
    Stop-Job -Job $PythonJob
    Remove-Job -Job $PythonJob
}

# If you need to manually stop and remove jobs when done, you can comment out the above and use below
# You would typically place these commands at the end of your script
# Stop-Job -Job $PythonJob
# Remove-Job -Job $PythonJob
