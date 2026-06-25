$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\src;$PSScriptRoot\scripts;$env:PYTHONPATH"
& py -3.9 -m unittest discover -s "$PSScriptRoot\tests" -q
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
