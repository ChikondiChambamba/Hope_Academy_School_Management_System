<#
.SYNOPSIS
    Build dist\Hope_Academy_School_Management_System.exe from Hope_Academy_School_Management_System.spec and,
    optionally, the Windows installer from school_managemt_setup.iss.

.EXAMPLE
    .\build_exe.ps1               # executable only
    .\build_exe.ps1 -Installer    # executable + installer\Hope_Academy_School_Management_System_Setup.exe
#>
param(
    [switch]$Installer
)

# Not 'Stop': PyInstaller logs progress to stderr, which Windows PowerShell 5.1
# turns into a terminating error. Failures are detected via $LASTEXITCODE below.
$ErrorActionPreference = 'Continue'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

# Prefer the project virtualenv so the build uses the pinned dependencies.
$python = Join-Path $here '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = 'python' }

$spec = 'Hope_Academy_School_Management_System.spec'
Write-Host "Building $spec with $python"
& $python -m PyInstaller --clean --noconfirm $spec
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller failed with exit code $LASTEXITCODE" -ForegroundColor Red
    exit $LASTEXITCODE
}
Write-Host 'Built dist\Hope_Academy_School_Management_System.exe' -ForegroundColor Green

if ($Installer) {
    $iscc = @(
        (Get-Command iscc -ErrorAction SilentlyContinue).Source,
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    ) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

    if (-not $iscc) {
        Write-Host 'Inno Setup 6 (ISCC.exe) not found. Install it from https://jrsoftware.org/isinfo.php' -ForegroundColor Red
        exit 1
    }
    & $iscc 'school_managemt_setup.iss'
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installer compilation failed with exit code $LASTEXITCODE" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host 'Built installer\Hope_Academy_School_Management_System_Setup.exe' -ForegroundColor Green
}
