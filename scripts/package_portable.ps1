$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PortableRoot = Join-Path $ProjectRoot "release\MercadoPagoColppy"
$ReleaseZip = Join-Path $ProjectRoot "release\MercadoPagoColppy-Windows.zip"
$ReleaseLauncher = Join-Path $ProjectRoot "release\Launcher.exe"
$ChecksumFile = Join-Path $ProjectRoot "release\SHA256SUMS.txt"
$AppExecutable = Join-Path $ProjectRoot "dist\MercadoPagoColppy.exe"
$LauncherExecutable = Join-Path $ProjectRoot "dist\MercadoPagoColppyLauncher.exe"

if (-not (Test-Path $AppExecutable)) {
    throw "No se encontro dist\MercadoPagoColppy.exe"
}
if (-not (Test-Path $LauncherExecutable)) {
    throw "No se encontro dist\MercadoPagoColppyLauncher.exe"
}

if (Test-Path $PortableRoot) {
    Remove-Item $PortableRoot -Recurse -Force
}
if (Test-Path $ReleaseZip) {
    Remove-Item $ReleaseZip -Force
}
if (Test-Path $ReleaseLauncher) {
    Remove-Item $ReleaseLauncher -Force
}
if (Test-Path $ChecksumFile) {
    Remove-Item $ChecksumFile -Force
}

New-Item -ItemType Directory -Force -Path $PortableRoot | Out-Null
Copy-Item $AppExecutable (Join-Path $PortableRoot "MercadoPagoColppy.exe")
Copy-Item (Join-Path $ProjectRoot "version.json") (Join-Path $PortableRoot "version.json")
Copy-Item $LauncherExecutable $ReleaseLauncher

$AllowedFiles = @(
    "MercadoPagoColppy.exe",
    "version.json"
)
$PackagedFiles = Get-ChildItem -Path $PortableRoot -File
$Unexpected = $PackagedFiles | Where-Object { $AllowedFiles -notcontains $_.Name }
if ($Unexpected) {
    throw "El paquete contiene archivos no permitidos: $($Unexpected.Name -join ', ')"
}
if ($PackagedFiles.Count -ne $AllowedFiles.Count) {
    throw "El paquete de la aplicacion no contiene exactamente los dos archivos permitidos"
}

Compress-Archive -Path (Join-Path $PortableRoot "*") -DestinationPath $ReleaseZip -CompressionLevel Optimal
$Hash = (Get-FileHash -Path $ReleaseZip -Algorithm SHA256).Hash.ToLowerInvariant()
"$Hash *MercadoPagoColppy-Windows.zip" | Set-Content -Path $ChecksumFile -Encoding ascii
Write-Host "Launcher creado: $ReleaseLauncher"
Write-Host "Paquete de actualizacion creado: $ReleaseZip"
Write-Host "Checksum creado: $ChecksumFile"
