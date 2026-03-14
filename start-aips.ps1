$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$backendDir = Join-Path $repoRoot "aips-api"
$frontendDir = Join-Path $repoRoot "aips-web"
$backendEnvPath = Join-Path $backendDir ".env"
$frontendEnvPath = Join-Path $frontendDir ".env"
$pythonExe = Join-Path $backendDir ".venv\\Scripts\\python.exe"

function Read-DotEnvFile([string]$Path) {
  $values = @{}

  if (-not (Test-Path $Path)) {
    return $values
  }

  foreach ($rawLine in Get-Content $Path) {
    $line = $rawLine.Trim()
    if (-not $line -or $line.StartsWith("#")) {
      continue
    }

    if ($line.StartsWith("export ")) {
      $line = $line.Substring(7).Trim()
    }

    $separatorIndex = $line.IndexOf("=")
    if ($separatorIndex -lt 1) {
      continue
    }

    $key = $line.Substring(0, $separatorIndex).Trim()
    $value = $line.Substring($separatorIndex + 1).Trim()
    if (-not $key) {
      continue
    }

    if (
      ($value.Length -ge 2) -and
      (
        ($value.StartsWith('"') -and $value.EndsWith('"')) -or
        ($value.StartsWith("'") -and $value.EndsWith("'"))
      )
    ) {
      $value = $value.Substring(1, $value.Length - 2)
    }

    $values[$key] = $value
  }

  return $values
}

function Read-DotEnvString($Values, [string]$Key, [string]$DefaultValue) {
  if ($Values.ContainsKey($Key)) {
    $value = [string]$Values[$Key]
    if ($value.Trim()) {
      return $value.Trim()
    }
  }

  return $DefaultValue
}

function Read-DotEnvInt($Values, [string]$Key, [int]$DefaultValue) {
  if ($Values.ContainsKey($Key)) {
    $value = 0
    if ([int]::TryParse([string]$Values[$Key], [ref]$value) -and $value -gt 0) {
      return $value
    }
  }

  return $DefaultValue
}

$backendEnv = Read-DotEnvFile $backendEnvPath
$frontendEnv = Read-DotEnvFile $frontendEnvPath
$backendHost = Read-DotEnvString $backendEnv "AIPS_API_HOST" "127.0.0.1"
$backendPort = Read-DotEnvInt $backendEnv "AIPS_API_PORT" 8000
$frontendHost = Read-DotEnvString $frontendEnv "VITE_APP_HOST" "127.0.0.1"
$frontendPort = Read-DotEnvInt $frontendEnv "VITE_APP_PORT" 5173
$frontendApiProxyTarget = Read-DotEnvString $frontendEnv "VITE_API_PROXY_TARGET" "http://$backendHost`:$backendPort"
$backendBaseUrl = "http://$backendHost`:$backendPort"

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

if ($frontendApiProxyTarget -ne $backendBaseUrl) {
  Write-Warning "VITE_API_PROXY_TARGET is $frontendApiProxyTarget, but the backend will start on $backendBaseUrl."
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
