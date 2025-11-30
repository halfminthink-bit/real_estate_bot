# Kokudo Suuchi Data Setup Script
# Move and extract downloaded ZIP files

Write-Host ("=" * 60)
Write-Host "Kokudo Suuchi Data Setup"
Write-Host ("=" * 60)

# Settings
$downloadFolder = "$env:USERPROFILE\Downloads"
$targetFolder = "data\raw\national\kokudo_suuchi"

# Generate years array from 2000 to 2020 (L01-00 to L01-20)
# Note: 2021-2025 are already processed
$years = @()
for ($year = 2000; $year -le 2020; $year++) {
    $yearCode = $year - 2000
    $yearCodeStr = $yearCode.ToString("00")
    $fileName = "L01-$yearCodeStr`_13_GML.zip"
    $years += @{Year=$year; File=$fileName}
}

# Step 1: Create folder
Write-Host "`n[Step 1] Create folder" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $targetFolder | Out-Null
Write-Host "  OK: Created $targetFolder"

# Step 2: Move ZIP files
Write-Host "`n[Step 2] Move ZIP files" -ForegroundColor Cyan
$movedCount = 0
foreach ($item in $years) {
    $sourceFile = Join-Path $downloadFolder $item.File
    $targetFile = Join-Path $targetFolder $item.File
    
    if (Test-Path $sourceFile) {
        Copy-Item -Path $sourceFile -Destination $targetFile -Force
        Write-Host "  OK: Moved $($item.File)"
        $movedCount++
    } else {
        Write-Host "  WARNING: $($item.File) not found (skipped)" -ForegroundColor Yellow
    }
}

if ($movedCount -eq 0) {
    Write-Host "  ERROR: No files to move" -ForegroundColor Red
    Write-Host "  -> Please check download folder: $downloadFolder"
    exit 1
}

# Step 3: Extract ZIP files
Write-Host "`n[Step 3] Extract ZIP files" -ForegroundColor Cyan
$extractedCount = 0
foreach ($item in $years) {
    $zipFile = Join-Path $targetFolder $item.File
    $extractPath = Join-Path $targetFolder "$($item.Year)_13"
    
    if (Test-Path $zipFile) {
        try {
            Expand-Archive -Path $zipFile -DestinationPath $extractPath -Force
            Write-Host "  OK: Extracted $($item.File) -> $($item.Year)_13"
            $extractedCount++
        } catch {
            Write-Host "  ERROR: Failed to extract $($item.File): $_" -ForegroundColor Red
        }
    }
}

# Step 4: Verify
Write-Host "`n[Step 4] Verify extraction" -ForegroundColor Cyan
$allFiles = Get-ChildItem -Path $targetFolder -Recurse -File
$zipFiles = $allFiles | Where-Object { $_.Extension -eq ".zip" }
$otherFiles = $allFiles | Where-Object { $_.Extension -ne ".zip" }

Write-Host "  ZIP files: $($zipFiles.Count)"
Write-Host "  Extracted files: $($otherFiles.Count)"

if ($otherFiles.Count -gt 0) {
    Write-Host "`n  Extracted files (first 10):" -ForegroundColor Green
    $otherFiles | Select-Object -First 10 | ForEach-Object {
        $relativePath = $_.FullName.Replace((Resolve-Path $targetFolder).Path + "\", "")
        Write-Host "    - $relativePath"
    }
    if ($otherFiles.Count -gt 10) {
        Write-Host "    ... and $($otherFiles.Count - 10) more files"
    }
}

Write-Host ""
Write-Host ("=" * 60)
Write-Host "Setup completed" -ForegroundColor Green
Write-Host ("=" * 60)
Write-Host "`nNext step:"
Write-Host "  -> Run scripts/02_download_data.py to convert to CSV"
