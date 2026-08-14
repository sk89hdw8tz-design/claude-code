<#
One-command runner for the whole pipeline (Windows PowerShell).

    .\run_all.ps1                        # the real sheets (profile galveston1889)
    .\run_all.ps1 -Profile synthetic     # the self-test fixture, end to end
    .\run_all.ps1 -From 06               # resume at a given step

On Windows, GDAL and its Python bindings are the usual source of pain. This
project deliberately avoids that: it uses rasterio's bundled GDAL and needs no
GDAL command-line tools and no OSGeo4W installation. A plain
`pip install -r requirements.txt` into a virtual environment is sufficient.
If you would rather use conda, `environment.yml` is provided and is the more
robust route if you also want the optional OSMnx step.
#>
[CmdletBinding()]
param(
    [string]$Profile = "galveston1889",
    [string]$From = "01",
    [string]$Python = "python"
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$steps = @(
    "01_fetch_sources.py",
    "02_inventory_sources.py",
    "03_build_sheet1_mask.py",
    "04_build_topology.py",
    "05_generate_reference_intersections.py",
    "06_detect_or_define_gcps.py",
    "07_fit_and_evaluate_transforms.py",
    "08_build_masks.py",
    "09_warp_sources.py",
    "10_build_mosaic.py",
    "11_quality_control.py",
    "12_export_final.py"
)

if ($Profile -eq "synthetic") {
    Write-Host "=== building the synthetic fixture first ===" -ForegroundColor Cyan
    & $Python "scripts/make_synthetic_fixture.py"
    if ($LASTEXITCODE -ne 0) { throw "fixture generation failed ($LASTEXITCODE)" }
}

foreach ($s in $steps) {
    $n = $s.Substring(0, 2)
    if ([int]$n -lt [int]$From) {
        Write-Host "--- skipping $s (before -From $From)" -ForegroundColor DarkGray
        continue
    }
    Write-Host ""
    Write-Host "==============================================================" -ForegroundColor Cyan
    Write-Host "=== $s   (profile: $Profile)" -ForegroundColor Cyan
    Write-Host "==============================================================" -ForegroundColor Cyan

    & $Python (Join-Path "scripts" $s) --profile $Profile
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Error "$s exited $LASTEXITCODE -- stopping. Read the message above and logs\."
        exit $LASTEXITCODE
    }
}

Write-Host ""
Write-Host "=== complete. Deliverables in output\ ===" -ForegroundColor Green
Get-ChildItem output | Format-Table Name, Length, LastWriteTime
