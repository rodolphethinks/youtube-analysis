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

# Start backend in a new PowerShell window
Write-Host "Starting FastAPI backend on http://localhost:8000..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\backend'; python -m uvicorn app:app --reload --port 8000"

# Wait a moment for backend to start
Start-Sleep -Seconds 2

# Start frontend in a new PowerShell window
Write-Host "Starting React frontend on http://localhost:5173..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD\frontend'; npm install; npm run dev"

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
Write-Host "Opening browser..." -ForegroundColor Gray

# Open browser
Start-Process "http://localhost:5173"

Write-Host ""
Write-Host "Press any key to stop the servers..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
