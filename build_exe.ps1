param(
    [string]$Entry = 'main.py',
    [string]$Icon = 'assets\school-management-software.ico',
    [string]$Name = 'Hope_Academy_School_Management_System',
    [switch]$Windowed
)

# Ensure script runs from repo root
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

Write-Host ('Build script running from: {0}' -f $here)

# Verify entrypoint exists
if (-not (Test-Path $Entry)) {
    Write-Host ("Error: Entrypoint '{0}' not found in {1}" -f $Entry, $here) -ForegroundColor Red
    exit 1
}

# Resolve icon: prefer provided, otherwise search assets for any .ico
if ($Icon -and (Test-Path $Icon)) {
    $resolvedIcon = (Resolve-Path $Icon).Path
} else {
    $found = Get-ChildItem -Path (Join-Path $here 'assets') -Filter *.ico -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($found) {
        $resolvedIcon = $found.FullName
    } else {
        $resolvedIcon = $null
    }
}

if ($resolvedIcon) {
    Write-Host ("Using icon: {0}" -f $resolvedIcon)
} else {
    Write-Host 'No .ico found - building without custom icon'
}

# Build args
$pyArgs = @('--clean', '--onefile')
if ($Windowed) { $pyArgs += '--noconsole' }
$pyArgs += @('-n', $Name)
if ($resolvedIcon) { $pyArgs += @('-i', $resolvedIcon) }
$pyArgs += $Entry

# Run via python -m PyInstaller for predictable interpreter
$exe = 'python'
$fullArgs = '-m PyInstaller ' + ($pyArgs -join ' ')
Write-Host ("Running: {0} {1}" -f $exe, $fullArgs)

$proc = Start-Process -FilePath $exe -ArgumentList $fullArgs -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) {
    Write-Host ("PyInstaller failed with exit code {0}" -f $($proc.ExitCode)) -ForegroundColor Red
    exit $proc.ExitCode
}

Write-Host ("Build completed. Check the 'dist' folder for the '{0}' executable." -f $Name) -ForegroundColor Green
