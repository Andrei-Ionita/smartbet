# Reset Next.js Development Environment
# Run this script when encountering ChunkLoadError

Write-Host "🔄 Resetting Next.js development environment..." -ForegroundColor Yellow

# Stop any running Next.js processes
Write-Host "⏹️  Stopping Next.js processes..." -ForegroundColor Cyan
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*next*" } | Stop-Process -Force

# Clear Next.js cache
Write-Host "🗑️  Clearing .next cache..." -ForegroundColor Cyan
if (Test-Path ".next") {
    Remove-Item -Recurse -Force .next
    Write-Host "✅ .next cache cleared" -ForegroundColor Green
}

# Clear node_modules/.cache if it exists
Write-Host "🗑️  Clearing node cache..." -ForegroundColor Cyan
if (Test-Path "node_modules/.cache") {
    Remove-Item -Recurse -Force "node_modules/.cache"
    Write-Host "✅ Node cache cleared" -ForegroundColor Green
}

# Start fresh development server
Write-Host "🚀 Starting fresh development server..." -ForegroundColor Cyan
npm run dev

Write-Host "✅ Development environment reset complete!" -ForegroundColor Green
Write-Host "🌐 Open http://localhost:3000 in a new incognito window" -ForegroundColor Yellow 