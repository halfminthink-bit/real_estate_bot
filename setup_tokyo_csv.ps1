# Tokyo Land Price CSV Setup Script
# Move downloaded CSV files to project directory

Write-Host ("=" * 60)
Write-Host "Tokyo Land Price CSV Setup"
Write-Host ("=" * 60)

# Settings
$downloadFolder = "$env:USERPROFILE\Downloads"
$targetFolder = "data\raw\prefecture\tokyo"

# File mapping (year -> filename pattern)
$files = @(
    @{Year=2025; Pattern="R7_chiten_data.csv"; Target="tokyo_land_price_2025.csv"},
    @{Year=2024; Pattern="R6kouji_chiten_data.csv"; Target="tokyo_land_price_2024.csv"},
    @{Year=2023; Pattern="R5kouji_chiten_data__3.csv"; Target="tokyo_land_price_2023.csv"},
    @{Year=2022; Pattern="R4kouji_chiten_data__3.csv"; Target="tokyo_land_price_2022.csv"},
    @{Year=2021; Pattern="R3kouji_chiten_data__3.csv"; Target="tokyo_land_price_2021.csv"}
)

# Step 1: Create folder
Write-Host "`n[Step 1] Create folder" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $targetFolder | Out-Null
Write-Host "  OK: Created $targetFolder"

# Step 2: Move CSV files
Write-Host "`n[Step 2] Move CSV files" -ForegroundColor Cyan
$movedCount = 0
foreach ($item in $files) {
    # Try to find file with pattern
    $sourceFiles = Get-ChildItem -Path $downloadFolder -Filter "*$($item.Pattern.Split('_')[0])*" -ErrorAction SilentlyContinue
    
    if ($sourceFiles) {
        $sourceFile = $sourceFiles[0].FullName
        $targetFile = Join-Path $targetFolder $item.Target
        
        if (Test-Path $sourceFile) {
            Copy-Item -Path $sourceFile -Destination $targetFile -Force
            Write-Host "  OK: Moved $($item.Pattern) -> $($item.Target)"
            $movedCount++
        }
    } else {
        # Try exact filename
        $sourceFile = Join-Path $downloadFolder $item.Pattern
        $targetFile = Join-Path $targetFolder $item.Target
        
        if (Test-Path $sourceFile) {
            Copy-Item -Path $sourceFile -Destination $targetFile -Force
            Write-Host "  OK: Moved $($item.Pattern) -> $($item.Target)"
            $movedCount++
        } else {
            Write-Host "  WARNING: $($item.Pattern) not found (skipped)" -ForegroundColor Yellow
        }
    }
}

if ($movedCount -eq 0) {
    Write-Host "  ERROR: No files to move" -ForegroundColor Red
    Write-Host "  -> Please check download folder: $downloadFolder"
    Write-Host "`n  Expected files:"
    foreach ($item in $files) {
        Write-Host "    - $($item.Pattern)"
    }
    exit 1
}

# Step 3: Verify
Write-Host "`n[Step 3] Verify files" -ForegroundColor Cyan
$csvFiles = Get-ChildItem -Path $targetFolder -Filter "*.csv"
Write-Host "  CSV files: $($csvFiles.Count)"
foreach ($file in $csvFiles) {
    Write-Host "    - $($file.Name)"
}

Write-Host ""
Write-Host ("=" * 60)
Write-Host "Setup completed" -ForegroundColor Green
Write-Host ("=" * 60)
Write-Host "`nNext step:"
Write-Host "  -> Run: python scripts/check_tokyo_csv.py"

