$ErrorActionPreference = "Stop"

# Register .fnw file association on Windows (current user).
# This does not require Administrator rights because it writes to HKCU.

$scriptPath = Join-Path $PSScriptRoot "fnw_open.cmd"
if (-not (Test-Path $scriptPath)) {
  throw "fnw_open.cmd not found at: $scriptPath"
}

$ext = ".fnw"
$progId = "FuncNodes.WorkerFile"
$description = "FuncNodes Worker File"

# Register extension -> ProgID
New-Item -Path "HKCU:\Software\Classes\$ext" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$ext" -Name "(Default)" -Value $progId

# Register ProgID description
New-Item -Path "HKCU:\Software\Classes\$progId" -Force | Out-Null
Set-ItemProperty -Path "HKCU:\Software\Classes\$progId" -Name "(Default)" -Value $description

# Register open command
$commandKey = "HKCU:\Software\Classes\$progId\shell\open\command"
New-Item -Path $commandKey -Force | Out-Null

# Quote the cmd path and forward the clicked file as %1
$commandValue = "`"$scriptPath`" `"%1`""
Set-ItemProperty -Path $commandKey -Name "(Default)" -Value $commandValue

Write-Host "Registered .fnw association for current user."
Write-Host "Double-click a .fnw file to open it via: $scriptPath"
