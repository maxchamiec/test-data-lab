# Setup script: creates .venv and installs dependencies ONLY in this project folder.
# If no system Python is found, downloads the official Windows embeddable Python
# into .python/ (also inside the project). Nothing is installed system-wide.

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$VenvPath = Join-Path $ProjectRoot ".venv"
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"

# Embeddable Python (project-local, no system install)
$PythonEmbedVersion = "3.12.10"
$Is64Bit = [Environment]::Is64BitOperatingSystem
$EmbedArch = if ($Is64Bit) { "amd64" } else { "win32" }
$EmbedZipName = "python-$PythonEmbedVersion-embed-$EmbedArch.zip"
$EmbedUrl = "https://www.python.org/ftp/python/$PythonEmbedVersion/$EmbedZipName"
$EmbedDir = Join-Path $ProjectRoot ".python"
$GetPipUrl = "https://bootstrap.pypa.io/get-pip.py"

function Find-SystemPython {
    foreach ($cmd in @("py", "python3", "python")) {
        try {
            $exe = Get-Command $cmd -ErrorAction SilentlyContinue
            if (-not $exe) { continue }
            if ($exe.Source -like "*WindowsApps*") { continue }
            $ver = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0 -or $ver -match "Python") { return $cmd }
        } catch {}
    }
    return $null
}

function Ensure-EmbeddablePython {
    $pythonExe = Join-Path $EmbedDir "python.exe"
    if (Test-Path $pythonExe) {
        Write-Host "Using existing embeddable Python in .python\" -ForegroundColor Cyan
        return $pythonExe
    }

    Write-Host "Downloading embeddable Python into .python\ (project folder only)..." -ForegroundColor Cyan
    $zipPath = Join-Path $ProjectRoot $EmbedZipName
    try {
        Invoke-WebRequest -Uri $EmbedUrl -OutFile $zipPath -UseBasicParsing
    } catch {
        Write-Host "Download failed: $_" -ForegroundColor Red
        exit 1
    }

    if (-not (Test-Path $EmbedDir)) { New-Item -ItemType Directory -Path $EmbedDir | Out-Null }
    Expand-Archive -Path $zipPath -DestinationPath $EmbedDir -Force
    Remove-Item $zipPath -Force -ErrorAction SilentlyContinue

    # Enable site-packages (uncomment "import site" in pythonXX._pth)
    $pthFiles = Get-ChildItem -Path $EmbedDir -Filter "*._pth" -ErrorAction SilentlyContinue
    foreach ($pth in $pthFiles) {
        $content = Get-Content $pth.FullName -Raw
        if ($content -match "#import site") {
            $content = $content -replace "#import site", "import site"
            Set-Content -Path $pth.FullName -Value $content.TrimEnd() -NoNewline
        }
    }

    # Install pip into embeddable Python
    $getPipPath = Join-Path $ProjectRoot "get-pip.py"
    Invoke-WebRequest -Uri $GetPipUrl -OutFile $getPipPath -UseBasicParsing
    $proc = Start-Process -FilePath $pythonExe -ArgumentList $getPipPath -WorkingDirectory $ProjectRoot -Wait -PassThru -NoNewWindow
    Remove-Item $getPipPath -Force -ErrorAction SilentlyContinue
    if ($proc.ExitCode -ne 0) { exit $proc.ExitCode }

    Write-Host "Embeddable Python ready in .python\" -ForegroundColor Green
    return $pythonExe
}

function New-VenvFromPython($pythonExe) {
    Write-Host "Creating virtual environment in .venv\ ..." -ForegroundColor Cyan
    # Embeddable may not include venv; use virtualenv
    $pipExe = Join-Path (Split-Path $pythonExe -Parent) "Scripts\pip.exe"
    if (-not (Test-Path $pipExe)) { $pipExe = $pythonExe; $pipArgs = @("-m", "pip") } else { $pipArgs = @() }
    $p = Start-Process -FilePath $pipExe -ArgumentList @($pipArgs + "install", "virtualenv", "--quiet") -WorkingDirectory $ProjectRoot -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { exit $p.ExitCode }
    $p = Start-Process -FilePath $pythonExe -ArgumentList "-m", "virtualenv", $VenvPath -WorkingDirectory $ProjectRoot -Wait -PassThru -NoNewWindow
    if ($p.ExitCode -ne 0) { exit $p.ExitCode }
}

# ----- Main -----

# If .venv already exists, only refresh dependencies
if (Test-Path (Join-Path $VenvPath "Scripts\python.exe")) {
    Write-Host "Virtual environment already exists. Installing/updating dependencies..." -ForegroundColor Cyan
    $pip = Join-Path $VenvPath "Scripts\pip.exe"
    & $pip install -r $RequirementsPath
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "Done. Run the app with: .\run_app.ps1" -ForegroundColor Green
    exit 0
}

# Create .venv using system Python or embeddable
$sysPy = Find-SystemPython
if ($sysPy) {
    Write-Host "Using system Python: $sysPy" -ForegroundColor Cyan
    if ($sysPy -eq "py") {
        & py -3 -m venv $VenvPath
    } else {
        & $sysPy -m venv $VenvPath
    }
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    $embedPy = Ensure-EmbeddablePython
    New-VenvFromPython $embedPy
}

$pip = Join-Path $VenvPath "Scripts\pip.exe"
if (-not (Test-Path $pip)) {
    Write-Host "pip not found in .venv. Trying ensurepip..." -ForegroundColor Yellow
    $venvPy = Join-Path $VenvPath "Scripts\python.exe"
    & $venvPy -m ensurepip --upgrade
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host "Installing dependencies into .venv\ (project folder only)..." -ForegroundColor Cyan
& $pip install -r $RequirementsPath
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Done. Run the app with: .\run_app.ps1" -ForegroundColor Green
