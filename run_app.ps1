# Run the web UI using the project's virtual environment and open Chrome.
# Run setup.ps1 first if you have not yet created .venv.

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$AppPy = Join-Path $ProjectRoot "app.py"
$Url = "http://127.0.0.1:5001"

if (-not (Test-Path $PythonExe)) {
    Write-Host "Virtual environment not found. Run first: .\setup.ps1" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $AppPy)) {
    Write-Host "app.py not found in: $ProjectRoot" -ForegroundColor Red
    exit 1
}

Write-Host "Starting server at $Url ..." -ForegroundColor Cyan
Start-Process -FilePath $PythonExe -ArgumentList $AppPy -WorkingDirectory $ProjectRoot -WindowStyle Normal

Start-Sleep -Seconds 2
Write-Host "Opening Chrome..." -ForegroundColor Cyan
Start-Process "chrome" $Url
