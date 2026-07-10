$env:PATH = "C:\Program Files\Git\bin;C:\Program Files\Git\cmd;" + $env:PATH
Set-Location "C:\Users\Asus\Documents\AIC"

Write-Host "=== Staging all files ===" -ForegroundColor Cyan
git add -A

Write-Host "=== Status ===" -ForegroundColor Cyan
git status --short

Write-Host "=== Committing ===" -ForegroundColor Cyan
git commit -m "Add raw data, databases, and pycache files"

Write-Host "=== Pushing ===" -ForegroundColor Cyan
git push origin main 2>&1

Write-Host "=== Done ===" -ForegroundColor Green
