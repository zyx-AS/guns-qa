param(
    [string]$GunsRepoUrl = "https://gitee.com/stylefeng/guns.git",
    [string]$GunsFallbackRepoUrl = "https://gitcode.com/javaguns/guns.git",
    [string]$GunsDefaultBranch = "master",
    [string]$GunsRef = "84272f5a324e0d7890d241d7ae9afa7398da49fa",
    [string]$TestClass = "cn.stylefeng.guns.core.security.BlackWhiteInterceptorTest"
)

$ErrorActionPreference = "Stop"
$pythonCommand = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCommand) {
    throw "python is required to run scripts/run_guns_unit_test.py"
}

$runnerScript = Join-Path $PSScriptRoot "run_guns_unit_test.py"
& $pythonCommand.Source $runnerScript `
    --guns-repo-url $GunsRepoUrl `
    --guns-fallback-repo-url $GunsFallbackRepoUrl `
    --guns-default-branch $GunsDefaultBranch `
    --guns-ref $GunsRef `
    --test-class $TestClass
exit $LASTEXITCODE
