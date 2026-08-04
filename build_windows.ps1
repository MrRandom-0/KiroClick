$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

python -m PyInstaller --noconfirm --clean --onedir --windowed --name KiroClick main.py
Copy-Item config.json dist\KiroClick\config.json -Force
Copy-Item README.md dist\KiroClick\README.md -Force
New-Item -ItemType Directory -Path dist\KiroClick\templates -Force | Out-Null
Copy-Item templates\README.txt dist\KiroClick\templates\README.txt -Force
Get-ChildItem templates -File | Where-Object { $_.Extension -in '.png', '.jpg', '.jpeg' } | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination dist\KiroClick\templates -Force
}

$Archive = Join-Path $ProjectDir "dist\KiroClick-Windows.zip"
if (Test-Path -LiteralPath $Archive) {
    Remove-Item -LiteralPath $Archive -Force
}
Compress-Archive -Path dist\KiroClick\* -DestinationPath $Archive

$SourceArchive = Join-Path $ProjectDir "dist\KiroClick-Source-v1.0.0.zip"
if (Test-Path -LiteralPath $SourceArchive) {
    Remove-Item -LiteralPath $SourceArchive -Force
}
$SourceItems = @(
    ".gitignore",
    "README.md",
    "requirements.txt",
    "requirements-dev.txt",
    "config.json",
    "main.py",
    "capture_template.py",
    "build_windows.ps1",
    "build_macos.sh",
    "kiro_click",
    "templates",
    "tests"
)
tar -a -cf $SourceArchive --exclude=__pycache__ --exclude=*.pyc $SourceItems
Write-Host "Built: $ProjectDir\dist\KiroClick\KiroClick.exe"
Write-Host "Zip:   $Archive"
Write-Host "Source: $SourceArchive"
