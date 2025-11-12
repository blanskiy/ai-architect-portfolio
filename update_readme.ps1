# Quick README Update Script
$date = Get-Date -Format "MMMM d, yyyy"
Write-Host "What did you accomplish today?" -ForegroundColor Yellow
$update = Read-Host "Update"

if ([string]::IsNullOrWhiteSpace($update)) {
    Write-Host "No update provided. Exiting." -ForegroundColor Red
    exit
}

Write-Host "Adding update to README.md..." -ForegroundColor Yellow
$readme = Get-Content "README.md" -Raw
$newUpdate = "**$date**: $update"

if ($readme -match "## Recent Updates") {
    $readme = $readme -replace "(## Recent Updates\s+)", "`$1$newUpdate`n`n"
    Set-Content "README.md" $readme -NoNewline
    Write-Host "  README updated!" -ForegroundColor Green
} else {
    Write-Host "  Could not find Recent Updates section" -ForegroundColor Yellow
}
