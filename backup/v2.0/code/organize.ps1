$ErrorActionPreference = 'Stop'
$repoRoot = (Get-Location).Path
$workspaceRoot = Split-Path $repoRoot -Parent
$backupRoot = Join-Path $repoRoot 'backup'
$moves = [System.Collections.Generic.List[object]]::new()
function Move-Archive([string]$source, [string]$destination) {
    $sourcePath = [IO.Path]::GetFullPath((Join-Path $repoRoot $source))
    $targetPath = [IO.Path]::GetFullPath((Join-Path $backupRoot $destination))
    if (-not $sourcePath.StartsWith($workspaceRoot + [IO.Path]::DirectorySeparatorChar) -or -not $targetPath.StartsWith($backupRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Archive path escapes workspace' }
    if (-not (Test-Path -LiteralPath $sourcePath)) { return }
    if (Test-Path -LiteralPath $targetPath) { throw "Archive target already exists: $destination" }
    $items = if (Test-Path -LiteralPath $sourcePath -PathType Container) { @(Get-ChildItem -LiteralPath $sourcePath -File -Recurse -Force) } else { @(Get-Item -LiteralPath $sourcePath) }
    $hashes = @($items | ForEach-Object { [pscustomobject]@{ file = [IO.Path]::GetRelativePath($sourcePath, $_.FullName); sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLower() } })
    New-Item -ItemType Directory -Path (Split-Path $targetPath -Parent) -Force | Out-Null
    Move-Item -LiteralPath $sourcePath -Destination $targetPath
    $moves.Add([pscustomobject]@{ source = $source; destination = ('backup/' + $destination.Replace('\','/')); files = $hashes })
}
# Preserve exact manifests and all legacy fixture bytes before keeping only live dependencies.
Move-Archive 'evaluation/archive' 'v2.0/evaluation/archive'
New-Item -ItemType Directory -Path 'evaluation/archive/fixtures_v2_1' -Force | Out-Null
foreach ($name in @('A04.eml','A05.eml','P05.eml','P02.eml','A08.eml','H01.eml')) {
    Copy-Item -LiteralPath "backup/v2.0/evaluation/archive/fixtures_v2_1/$name" -Destination "evaluation/archive/fixtures_v2_1/$name"
}
foreach ($name in @('supplement_v2.jsonl','supplement_v2_revision2.jsonl','multi_action_draft.jsonl','real_data_candidates')) { Move-Archive "evaluation/$name" "v2.0/evaluation/$name" }
Move-Archive 'evaluation/fixtures_supplement/S10.eml' 'v2.0/evaluation/fixtures_supplement/S10.eml'
Copy-Item -LiteralPath 'evaluation/fixtures_supplement/S10_revision2.eml' -Destination 'backup/v2.0/evaluation/fixtures_supplement/S10_revision2.eml'
foreach ($file in @(Get-ChildItem evaluation -File -Filter 'cases_v*.jsonl')) {
    $version = ([regex]::Match($file.Name,'v(\d+)_(\d+)')).Groups
    Move-Archive "evaluation/$($file.Name)" "v$($version[1].Value).$($version[2].Value)/evaluation/$($file.Name)"
}
foreach ($file in @(Get-ChildItem evaluation -File -Filter 'annotation_policy_v*.md')) {
    $version = ([regex]::Match($file.Name,'v(\d+)_(\d+)')).Groups
    Move-Archive "evaluation/$($file.Name)" "v$($version[1].Value).$($version[2].Value)/docs/$($file.Name)"
}
Move-Archive 'evaluation/annotation_policy.md' 'v1.5/docs/annotation_policy.md'
$manifestVersions = @{}
foreach ($file in Get-ChildItem backup -File -Recurse -Filter 'cases_v*.jsonl') {
    $version = ([regex]::Match($file.Name,'v(\d+)_(\d+)')).Groups
    $manifestVersions[(Get-FileHash -LiteralPath $file.FullName).Hash.ToLower()] = "v$($version[1].Value).$($version[2].Value)"
}
foreach ($directory in @(Get-ChildItem results/evaluation -Directory)) {
    if ($directory.Name -eq 'v2-regression-repair-20261001') { continue }
    $meta = Get-Content -LiteralPath (Join-Path $directory.FullName 'run.json') -Raw | ConvertFrom-Json
    $version = if ($meta.schema -eq 'v2' -or $directory.Name -match 'v2|challenge') { 'v2.0' } elseif ($manifestVersions.ContainsKey($meta.manifest_sha256)) { $manifestVersions[$meta.manifest_sha256] } else { 'v1.0' }
    Move-Archive "results/evaluation/$($directory.Name)" "$version/results/evaluation/$($directory.Name)"
}
foreach ($file in @(Get-ChildItem docs -File)) { Move-Archive "docs/$($file.Name)" "v2.0/docs/$($file.Name)" }
Move-Archive 'README.md' 'v2.0/docs/README-before-freeze.md'
foreach ($file in @(Get-ChildItem tools -File)) { Move-Archive "tools/$($file.Name)" "v2.0/code/tools/$($file.Name)" }
Move-Archive 'src/actionmail.egg-info' 'v2.0/code/generated/actionmail.egg-info'
Move-Archive '../ARCHITECTURE.md' 'v1.0/docs/ARCHITECTURE.md'
Move-Archive '../PROJECT_RESTART_BRIEF.md' 'v1.0/docs/PROJECT_RESTART_BRIEF.md'
Move-Archive '../ActionMail.zip' 'legacy/code/ActionMail.zip'
Move-Archive '../data.zip' 'legacy/data/data.zip'
foreach ($name in @('dev','test','train','full_data','prompt_data.txt')) { Move-Archive "../data/$name" "v1.5/data/mailex/$name" }
foreach ($file in @(Get-ChildItem ../data -File)) { Move-Archive "../data/$($file.Name)" "v2.0/data/provenance/$($file.Name)" }
foreach ($file in @(Get-ChildItem ../data/external_samples -File)) {
    if ($file.Name -notin @('496fbb1c751d22557bfd74a63732c608.parent.json','enron_nov25.pdf')) { Move-Archive "../data/external_samples/$($file.Name)" "v2.0/data/external_samples/$($file.Name)" }
}
# Course originals are current source material, retained locally instead of redistributed.
New-Item -ItemType Directory -Path 'docs/course' -Force | Out-Null
foreach ($file in @(Get-ChildItem $workspaceRoot -File | Where-Object { $_.Name -like 'PE6201_*' })) {
    $target = [IO.Path]::GetFullPath((Join-Path $repoRoot "docs/course/$($file.Name)"))
    if (-not $target.StartsWith($repoRoot + [IO.Path]::DirectorySeparatorChar)) { throw 'Course target escapes repository' }
    Move-Item -LiteralPath $file.FullName -Destination $target
}
$moves | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath 'backup/migration.json' -Encoding utf8
Write-Output "Archived $($moves.Count) paths. Current manifests and latest result records retain their original bytes."
