$ErrorActionPreference = 'Stop'
Import-Module -Name (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1')
$bridgeRoot = $PSScriptRoot
if (-not (Get-Process -Name 'Langflow' -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath 'E:\tools\langflow\Langflow .exe' -WindowStyle Hidden
}
if (-not (Get-Process -Name 'ollama' -ErrorAction SilentlyContinue)) {
  Start-Process -FilePath 'C:\Users\78052\AppData\Local\Programs\Ollama\ollama.exe' -ArgumentList 'serve' -WindowStyle Hidden
}
if (Test-Path -LiteralPath (Join-Path $bridgeRoot 'stop.flag')) { Remove-Item -LiteralPath (Join-Path $bridgeRoot 'stop.flag') }
$settings = Get-Content -LiteralPath (Join-Path $bridgeRoot 'config.json') -Raw | ConvertFrom-Json
$secureSecret = ConvertTo-SecureString -String $settings.protected_secret
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
try { $bridgeSecret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
$payload = @{ site_url = $settings.site_url; secret = $bridgeSecret } | ConvertTo-Json -Compress
$startInfo = [Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $settings.python
$startInfo.Arguments = '"' + (Join-Path $bridgeRoot 'bridge.py') + '"'
$startInfo.WorkingDirectory = $bridgeRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardInput = $true
$process = [Diagnostics.Process]::Start($startInfo)
$process.StandardInput.WriteLine($payload)
$process.StandardInput.Close()
$bridgeSecret = $null; $payload = $null
$process.WaitForExit()
