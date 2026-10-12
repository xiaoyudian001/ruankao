$ErrorActionPreference = 'Stop'
Import-Module -Name (Join-Path $PSHOME 'Modules\Microsoft.PowerShell.Security\Microsoft.PowerShell.Security.psd1')
$settings = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'config.json') -Raw | ConvertFrom-Json
$secure = ConvertTo-SecureString -String $settings.protected_secret
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
try { $secret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer) }
$payload = @{site_url=$settings.site_url; secret=$secret} | ConvertTo-Json -Compress
$payload | & $settings.python (Join-Path $PSScriptRoot 'diagnose_connection.py')
$secret=$null; $payload=$null
