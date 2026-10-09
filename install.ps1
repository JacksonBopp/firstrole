# job-search-os installer for Windows. Paste this into PowerShell:
#   irm https://raw.githubusercontent.com/JacksonBopp/job-search-os/main/install.ps1 | iex
#
# It installs Python if needed (via winget), puts job-search-os in its own folder
# (~\job-search-os), adds a "Job Search" shortcut to your desktop, and starts it.
# Run it again any time to update. Nothing needs admin rights.

$ErrorActionPreference = "Stop"
$Dir = if ($env:JOBOS_INSTALL_DIR) { $env:JOBOS_INSTALL_DIR } else { Join-Path $HOME "job-search-os" }
$Source = if ($env:JOBOS_SOURCE) { $env:JOBOS_SOURCE } else { "https://github.com/JacksonBopp/job-search-os/archive/refs/heads/main.zip" }

function Get-Python {
    foreach ($cmd in "py", "python") {
        if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { continue }
        $pyArgs = @()
        if ($cmd -eq "py") { $pyArgs = @("-3") }
        try {
            $exe = & $cmd @pyArgs -c "import sys; print(sys.executable if sys.version_info >= (3, 10) else '')" 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { return "$exe".Trim() }
        } catch { }   # the Microsoft Store "python" placeholder fails here; that's fine
    }
    return $null
}

Write-Host "Installing job-search-os..." -ForegroundColor Cyan
$Python = Get-Python
if (-not $Python) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Host "Python is needed. Install it from https://www.python.org/downloads/ (check 'Add python.exe to PATH'), then run this again." -ForegroundColor Yellow
        return
    }
    Write-Host "Installing Python (one time, about a minute)..."
    winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements | Out-Null
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "User") + ";" + [Environment]::GetEnvironmentVariable("Path", "Machine")
    $Python = Get-Python
    if (-not $Python) {
        Write-Host "Python was installed, but this window can't see it yet. Close PowerShell, open a new one, and paste the line again." -ForegroundColor Yellow
        return
    }
}

New-Item -ItemType Directory -Force -Path $Dir | Out-Null
$Venv = Join-Path $Dir ".venv"
if (-not (Test-Path (Join-Path $Venv "Scripts\python.exe"))) { & $Python -m venv $Venv }
$VenvPython = Join-Path $Venv "Scripts\python.exe"
& $VenvPython -m pip install --upgrade --quiet --disable-pip-version-check $Source
if ($LASTEXITCODE -ne 0) { Write-Host "Install failed (see the message above)." -ForegroundColor Red; return }

if (-not $env:JOBOS_NO_SHORTCUT) {
    $Shell = New-Object -ComObject WScript.Shell
    $Link = $Shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath("Desktop")) "Job Search.lnk"))
    $Link.TargetPath = $VenvPython
    $Link.Arguments = "-m jobos"
    $Link.WorkingDirectory = $Dir
    $Link.Description = "Find and track jobs"
    $Link.Save()
    Write-Host "Added a 'Job Search' shortcut to your desktop."
}

Write-Host "Done! Your job list lives in $Dir" -ForegroundColor Green
if (-not $env:JOBOS_NO_LAUNCH) {
    Set-Location $Dir
    & $VenvPython -m jobos
}
