Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Autonomous Resilience Framework backend is booting." -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Swagger UI available at: http://127.0.0.1:8000/docs" -ForegroundColor Green
Write-Host ""

uvicorn backend.app.main:app --reload