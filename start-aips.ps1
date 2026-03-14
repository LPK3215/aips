$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $repoRoot "aips.settings.json"

if (-not (Test-Path $configPath)) {
  throw "Startup config was not found: $configPath"
}

$settings = Get-Content $configPath -Raw | ConvertFrom-Json
$backendHost = [string]$settings.backend.host
$backendPort = [int]$settings.backend.port
$frontendHost = [string]$settings.frontend.host
$frontendPort = [int]$settings.frontend.port
$openBrowser = [bool]$settings.launcher.open_browser

$backendDir = Join-Path $repoRoot "aips-api"
$frontendDir = Join-Path $repoRoot "aips-web"
$pythonExe = Join-Path $backendDir ".venv\\Scripts\\python.exe"

if (-not (Test-Path $pythonExe)) {
  throw "Backend Python was not found: $pythonExe. Create aips-api\\.venv and install dependencies first."
}

$npmCmd = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npmCmd) {
  throw "npm.cmd was not found. Install Node.js first."
}

$frontendNodeModules = Join-Path $frontendDir "node_modules"
if (-not (Test-Path $frontendNodeModules)) {
  throw "Frontend dependencies were not found: $frontendNodeModules. Run npm install in aips-web first."
}

function Test-PortBusy([int]$Port) {
  return [bool](Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.LocalPort -eq $Port })
}

if (Test-PortBusy $backendPort) {
  throw "Backend port $backendPort is already in use. Stop the existing process first."
}

if (Test-PortBusy $frontendPort) {
  throw "Frontend port $frontendPort is already in use. Stop the existing process first."
}

$shellExe = (Get-Command powershell.exe).Source
$backendCommand = "Set-Location '$backendDir'; & '$pythonExe' -m app.run_dev"
$frontendCommand = "Set-Location '$frontendDir'; & '$($npmCmd.Source)' run dev"

$backendProcess = Start-Process -FilePath $shellExe -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy",
  "Bypass",
  "-Command",
  $backendCommand
) -PassThru

Start-Sleep -Seconds 2

$frontendProcess = Start-Process -FilePath $shellExe -ArgumentList @(
  "-NoExit",
  "-ExecutionPolicy",
  "Bypass",
  "-Command",
  $frontendCommand
) -PassThru

Write-Host ""
Write-Host "AIPS started:"
Write-Host "Backend: http://$backendHost`:$backendPort"
Write-Host "Frontend: http://$frontendHost`:$frontendPort"
Write-Host "Backend window PID: $($backendProcess.Id)"
Write-Host "Frontend window PID: $($frontendProcess.Id)"

if ($openBrowser) {
  Start-Sleep -Seconds 3
  Start-Process "http://$frontendHost`:$frontendPort"
}
