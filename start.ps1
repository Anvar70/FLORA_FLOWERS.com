$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$flowerPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $flowerPython)) { $flowerPython = 'python' }
& $flowerPython manage.py migrate
& $flowerPython manage.py createcachetable
& $flowerPython manage.py seed_demo
& $flowerPython manage.py runserver 127.0.0.1:8000

