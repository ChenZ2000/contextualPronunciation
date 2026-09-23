$ErrorActionPreference = "Stop"

Push-Location -LiteralPath $PSScriptRoot
try {
	python scripts/run_tests.py
	if ($LASTEXITCODE -ne 0) {
		exit $LASTEXITCODE
	}
	python scripts/build_addon.py
	exit $LASTEXITCODE
}
finally {
	Pop-Location
}
