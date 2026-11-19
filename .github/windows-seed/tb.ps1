param(
    [Parameter(Mandatory, Position = 0)]
    [string] $Source,
    [Alias('o')]
    [string] $OutputPath
)

$ErrorActionPreference = 'Stop'
$sourceFile = (Resolve-Path -LiteralPath $Source).ProviderPath
if (!$OutputPath) {
    $OutputPath = [IO.Path]::ChangeExtension($sourceFile, '.exe')
}
$outputFile = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($OutputPath)
$compiler = Join-Path $PSScriptRoot 'tb.exe'
$adapter = Join-Path $PSScriptRoot 'target_ir.py'
$shim = Join-Path $PSScriptRoot 'crt.c'
$python = (Get-Command python -CommandType Application).Source | Select-Object -First 1
$clang = (Get-Command clang -CommandType Application).Source | Select-Object -First 1
$work = New-Item -ItemType Directory -Path (Join-Path ([IO.Path]::GetTempPath()) ('tb-' + [guid]::NewGuid()))
try {
    $raw = (Join-Path $work.FullName 'program.raw.ll').Replace('\', '/')
    $ir = Join-Path $work.FullName 'program.ll'
    & $compiler $sourceFile.Replace('\', '/') $raw
    if ($LASTEXITCODE -ne 0) { throw "tb compilation failed ($LASTEXITCODE)" }
    & $python $adapter $raw $ir
    if ($LASTEXITCODE -ne 0) { throw "Windows IR adaptation failed ($LASTEXITCODE)" }

    $objects = @()
    $cflags = @(Get-Content -LiteralPath "$raw.cflags" | Where-Object { $_ })
    foreach ($csource in (Get-Content -LiteralPath "$raw.csources" | Where-Object { $_ })) {
        $object = Join-Path $work.FullName ("runtime-" + $objects.Count + '.obj')
        & $clang @cflags -c $csource -o $object
        if ($LASTEXITCODE -ne 0) { throw "Runtime compilation failed ($LASTEXITCODE)" }
        $objects += $object
    }
    $linkflags = @(Get-Content -LiteralPath "$raw.linkflags" | Where-Object { $_ })
    & $clang '-Wl,--stack,16777216' -O2 $ir $shim @objects @linkflags -o $outputFile
    if ($LASTEXITCODE -ne 0) { throw "Native link failed ($LASTEXITCODE)" }
} finally {
    Remove-Item -LiteralPath $work.FullName -Recurse -Force
}
