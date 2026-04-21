param(
    [string]$GunsRepoUrl = "https://gitee.com/stylefeng/guns.git",
    [string]$GunsFallbackRepoUrl = "https://gitcode.com/javaguns/guns.git",
    [string]$GunsDefaultBranch = "master",
    [string]$GunsRef = "84272f5a324e0d7890d241d7ae9afa7398da49fa",
    [string]$TestClass = "cn.stylefeng.guns.core.security.BlackWhiteInterceptorTest"
)

$ErrorActionPreference = "Stop"

$rootDir = Split-Path -Parent $PSScriptRoot
$workDir = Join-Path $rootDir ".tmp\\guns-src"
$artifactDir = Join-Path $rootDir ".artifacts\\guns"
$m2Cache = Join-Path $rootDir ".tmp\\m2\\repository"
$mavenVersion = "3.9.9"
$mavenHome = Join-Path $rootDir ".tmp\\tools\\apache-maven-$mavenVersion"
$mavenArchive = Join-Path $rootDir ".tmp\\tools\\apache-maven-$mavenVersion-bin.zip"

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $workDir), $artifactDir, $m2Cache | Out-Null
if (Test-Path $workDir) {
    Remove-Item -LiteralPath $workDir -Recurse -Force
}

function Clone-GunsRepo {
    param([string[]]$RepoUrls)

    foreach ($repoUrl in $RepoUrls) {
        if ([string]::IsNullOrWhiteSpace($repoUrl)) {
            continue
        }

        Write-Host "Cloning GUNS from $repoUrl"
        & git clone --depth 1 --branch $GunsDefaultBranch $repoUrl $workDir
        if ($LASTEXITCODE -eq 0) {
            return
        }

        if (Test-Path $workDir) {
            Remove-Item -LiteralPath $workDir -Recurse -Force
        }
    }

    throw "Unable to clone the GUNS repository."
}

Clone-GunsRepo -RepoUrls @($GunsRepoUrl, $GunsFallbackRepoUrl)

$resolvedHead = (& git -C $workDir rev-parse HEAD).Trim()
if ($GunsRef -ne $resolvedHead) {
    & git -C $workDir fetch --depth 1 origin $GunsRef
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to fetch GUNS ref $GunsRef"
    }

    & git -C $workDir checkout --detach FETCH_HEAD
    if ($LASTEXITCODE -ne 0) {
        throw "Failed to check out GUNS ref $GunsRef"
    }

    $resolvedHead = (& git -C $workDir rev-parse HEAD).Trim()
}

$testAssetsDir = Join-Path $rootDir "guns-tests"
if (Test-Path $testAssetsDir) {
    Write-Host "Copying test assets from guns-qa into the GUNS workspace"
    Copy-Item -Path (Join-Path $testAssetsDir "*") -Destination $workDir -Recurse -Force
}

$expectedTestPath = Join-Path $workDir "src\\test\\java\\cn\\stylefeng\\guns\\core\\security\\BlackWhiteInterceptorTest.java"
if (-not (Test-Path $expectedTestPath)) {
    throw "Expected test asset was not copied into the GUNS workspace: $expectedTestPath"
}

function Get-PortableMaven {
    $mavenCmd = Join-Path $mavenHome "bin\\mvn.cmd"
    if (Test-Path $mavenCmd) {
        return $mavenCmd
    }

    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $mavenHome) | Out-Null
    $archiveUrl = "https://archive.apache.org/dist/maven/maven-3/$mavenVersion/binaries/apache-maven-$mavenVersion-bin.zip"
    Write-Host "Downloading portable Maven $mavenVersion"
    Invoke-WebRequest -Uri $archiveUrl -OutFile $mavenArchive
    Expand-Archive -LiteralPath $mavenArchive -DestinationPath (Split-Path -Parent $mavenHome) -Force
    return $mavenCmd
}

function Invoke-MavenTest {
    param([string]$MavenCommand)

    Push-Location $workDir
    try {
        & $MavenCommand -B -ntp "-Dtest=$TestClass" test
        if ($LASTEXITCODE -ne 0) {
            throw "Maven test execution failed."
        }
    }
    finally {
        Pop-Location
    }
}

$dockerReady = $false
if (Get-Command docker -ErrorAction SilentlyContinue) {
    cmd /c "docker info >nul 2>nul"
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
    }
}

if (Get-Command mvn -ErrorAction SilentlyContinue) {
    Invoke-MavenTest -MavenCommand "mvn"
}
elseif ($dockerReady) {
    & docker run --rm `
        -v "${workDir}:/workspace" `
        -v "${m2Cache}:/root/.m2/repository" `
        -w /workspace `
        maven:3.9.9-eclipse-temurin-17 `
        mvn -B -ntp "-Dtest=$TestClass" test

    if ($LASTEXITCODE -ne 0) {
        throw "Docker-based Maven test execution failed."
    }
}
else {
    $portableMaven = Get-PortableMaven
    Invoke-MavenTest -MavenCommand $portableMaven
}

$surefireDir = Join-Path $workDir "target\\surefire-reports"
if (Test-Path $surefireDir) {
    $artifactReports = Join-Path $artifactDir "surefire-reports"
    if (Test-Path $artifactReports) {
        Remove-Item -LiteralPath $artifactReports -Recurse -Force
    }
    Copy-Item -LiteralPath $surefireDir -Destination $artifactDir -Recurse
}

$metadata = @(
    "GUNS repo: $GunsRepoUrl"
    "Fallback repo: $GunsFallbackRepoUrl"
    "Pinned ref: $GunsRef"
    "Resolved commit: $resolvedHead"
    "Selected test: $TestClass"
    "Workspace: $workDir"
    "Artifacts: $artifactDir"
)

Set-Content -LiteralPath (Join-Path $artifactDir "run-metadata.txt") -Value $metadata -Encoding UTF8
Write-Host "Run completed successfully."
