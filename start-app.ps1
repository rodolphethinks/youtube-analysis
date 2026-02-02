# YouTube Video Intelligence - Start Script
# Run this from the project root directory

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  YouTube Video Intelligence Platform  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check for GOOGLE_API_KEY
if (-not $env:GOOGLE_API_KEY) {
    Write-Host "WARNING: GOOGLE_API_KEY environment variable not set!" -ForegroundColor Yellow
    Write-Host "Set it with: `$env:GOOGLE_API_KEY='your-api-key'" -ForegroundColor Yellow
    Write-Host ""
}

# Store process IDs for cleanup
$script:backendProcess = $null
$script:frontendProcess = $null

# Cleanup function
function Stop-Servers {
    Write-Host ""
    Write-Host "Stopping servers..." -ForegroundColor Yellow
    
    # Stop backend
    if ($script:backendProcess -and !$script:backendProcess.HasExited) {
        Write-Host "Stopping backend (PID: $($script:backendProcess.Id))..." -ForegroundColor Gray
        Stop-Process -Id $script:backendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    # Stop frontend
    if ($script:frontendProcess -and !$script:frontendProcess.HasExited) {
        Write-Host "Stopping frontend (PID: $($script:frontendProcess.Id))..." -ForegroundColor Gray
        Stop-Process -Id $script:frontendProcess.Id -Force -ErrorAction SilentlyContinue
    }
    
    # Also kill any orphaned processes on our ports
    $backendPort = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($backendPort) {
        Stop-Process -Id $backendPort -Force -ErrorAction SilentlyContinue
    }
    
    $frontendPort = Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique
    if ($frontendPort) {
        Stop-Process -Id $frontendPort -Force -ErrorAction SilentlyContinue
    }
    
    Write-Host "Servers stopped." -ForegroundColor Green
}

# Register cleanup on script exit
$null = Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-Servers }

try {
    # Start backend
    Write-Host "Starting FastAPI backend on http://localhost:8000..." -ForegroundColor Green
    $script:backendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; & '$PWD\venv\Scripts\python.exe' -m uvicorn app:app --reload --port 8000" -PassThru

    # Wait a moment for backend to start
    Start-Sleep -Seconds 3

    # Start frontend
    Write-Host "Starting React frontend on http://localhost:5173..." -ForegroundColor Green
    $script:frontendProcess = Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm install; npm run dev" -PassThru

    # Wait for frontend to be ready
    Start-Sleep -Seconds 5

    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Application Started!                 " -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Backend API:  http://localhost:8000" -ForegroundColor White
    Write-Host "Frontend UI:  http://localhost:5173" -ForegroundColor White
    Write-Host ""
    Write-Host "Backend PID:  $($script:backendProcess.Id)" -ForegroundColor Gray
    Write-Host "Frontend PID: $($script:frontendProcess.Id)" -ForegroundColor Gray
    Write-Host ""
    Write-Host "Opening browser..." -ForegroundColor Gray

    # Open browser
    Start-Process "http://localhost:5173"

    Write-Host ""
    Write-Host "Press Ctrl+C or any key to stop the servers..." -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
}
finally {
    # Ensure cleanup runs even on Ctrl+C
    Stop-Servers
}
