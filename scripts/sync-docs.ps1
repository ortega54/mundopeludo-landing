# Copia el sitio de la raiz del repo a docs/ (misma logica que .github/workflows/sync-docs.yml).
# Uso: .\scripts\sync-docs.ps1   o   doble clic en scripts\sync-docs.cmd

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root
$docs = Join-Path $root "docs"

New-Item -ItemType Directory -Force -Path $docs | Out-Null
Copy-Item -Path (Join-Path $root "index.html") -Destination $docs -Force
Copy-Item -Path (Join-Path $root "styles.css") -Destination $docs -Force

$nojekyllSrc = Join-Path $root ".nojekyll"
if (Test-Path $nojekyllSrc) {
  Copy-Item -Path $nojekyllSrc -Destination $docs -Force
} else {
  New-Item -Path (Join-Path $docs ".nojekyll") -ItemType File -Force | Out-Null
}

$img = Join-Path $docs "images"
$med = Join-Path $docs "media"
if (Test-Path $img) { Remove-Item $img -Recurse -Force }
if (Test-Path $med) { Remove-Item $med -Recurse -Force }

$imagesSrc = Join-Path $root "images"
$mediaSrc = Join-Path $root "media"
if (Test-Path $imagesSrc) { Copy-Item -Path $imagesSrc -Destination $docs -Recurse -Force }
if (Test-Path $mediaSrc) { Copy-Item -Path $mediaSrc -Destination $docs -Recurse -Force }

Write-Host "Listo: docs/ esta igual que la raiz (index, CSS, images, media)."
