$path = ".\services\analysis_orchestrator.py"
$lines = [System.IO.File]::ReadAllLines($path)
$start = -1

for ($i = 0; $i -lt $lines.Length; $i++) {
    if ($lines[$i] -match '^#\s*from __future__ import annotations\s*$') {
        $start = $i
        break
    }
}

if ($start -lt 0) {
    throw "Commented original code marker not found."
}

$restored = [System.Collections.Generic.List[string]]::new()

for ($i = $start; $i -lt $lines.Length; $i++) {
    $line = $lines[$i]
    if ($line.StartsWith("#")) {
        $line = $line.Substring(1)
        if ($line.StartsWith(" ")) {
            $line = $line.Substring(1)
        }
    }
    $restored.Add($line)
}

$utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false
[System.IO.File]::WriteAllLines($path, $restored.ToArray(), $utf8)
