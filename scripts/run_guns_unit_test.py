#!/usr/bin/env python3
"""Cross-platform runner for the selected GUNS unit test."""

from __future__ import annotations

import argparse
import json
import os
import stat
import shutil
import subprocess
import sys
import tarfile
import traceback
import urllib.request
import xml.etree.ElementTree as element_tree
import zipfile
from pathlib import Path

from guns_ci import ensure_dir, write_json, write_text

JACOCO_MAVEN_PLUGIN_VERSION = "0.8.12"


def env_default(name: str, fallback: str) -> str:
    return os.environ.get(name, fallback)


def env_list(name: str) -> list[str]:
    raw_value = os.environ.get(name, "").strip()
    if not raw_value:
        return []

    try:
        decoded = json.loads(raw_value)
    except json.JSONDecodeError:
        decoded = raw_value

    if isinstance(decoded, list):
        return [str(item).strip() for item in decoded if str(item).strip()]
    if isinstance(decoded, str) and decoded.strip():
        normalized = decoded.replace("\r", "\n").replace(";", ",").replace("\n", ",")
        return [item.strip() for item in normalized.split(",") if item.strip()]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guns-repo-url", default=env_default("GUNS_REPO_URL", "https://gitee.com/stylefeng/guns.git"))
    parser.add_argument(
        "--guns-fallback-repo-url",
        default=env_default("GUNS_FALLBACK_REPO_URL", "https://gitcode.com/javaguns/guns.git"),
    )
    parser.add_argument("--guns-default-branch", default=env_default("GUNS_DEFAULT_BRANCH", "master"))
    parser.add_argument(
        "--guns-ref",
        default=env_default("GUNS_REF", "84272f5a324e0d7890d241d7ae9afa7398da49fa"),
    )
    parser.add_argument(
        "--test-class",
        default=env_default("GUNS_TEST_CLASS", ""),
    )
    parser.add_argument("--guns-work-dir", default=env_default("GUNS_WORK_DIR", ""))
    parser.add_argument("--guns-artifact-dir", default=env_default("GUNS_ARTIFACT_DIR", ""))
    parser.add_argument("--local-m2-cache", default=env_default("LOCAL_M2_CACHE", ""))
    parser.add_argument("--maven-version", default=env_default("MAVEN_VERSION", "3.9.9"))
    parser.add_argument("--coverage-class", action="append", default=[])
    parser.add_argument("--root-dir", default="")
    return parser.parse_args()


def run_command(command: list[str], cwd: Path | None = None) -> int:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, check=False).returncode


def handle_remove_readonly(function, path, _exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    function(path)


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path, onerror=handle_remove_readonly)


def capture_command(command: list[str], cwd: Path | None = None) -> str:
    completed = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        capture_output=True,
    )
    return completed.stdout.strip()


def clone_repo(work_dir: Path, repo_urls: list[str], default_branch: str) -> None:
    for repo_url in repo_urls:
        if not repo_url.strip():
            continue
        print(f"Cloning GUNS from {repo_url}")
        if run_command(["git", "clone", "--depth", "1", "--branch", default_branch, repo_url, str(work_dir)]) == 0:
            return
        remove_tree(work_dir)
        print(f"Clone failed for {repo_url}", file=sys.stderr)
    raise RuntimeError("Unable to clone the GUNS repository.")


def resolve_head(work_dir: Path, guns_ref: str) -> str:
    resolved_head = capture_command(["git", "-C", str(work_dir), "rev-parse", "HEAD"])
    if guns_ref != resolved_head:
        if run_command(["git", "-C", str(work_dir), "fetch", "--depth", "1", "origin", guns_ref]) != 0:
            raise RuntimeError(f"Failed to fetch GUNS ref {guns_ref}")
        if run_command(["git", "-C", str(work_dir), "checkout", "--detach", "FETCH_HEAD"]) != 0:
            raise RuntimeError(f"Failed to check out GUNS ref {guns_ref}")
        resolved_head = capture_command(["git", "-C", str(work_dir), "rev-parse", "HEAD"])
    return resolved_head


def copy_test_assets(root_dir: Path, work_dir: Path) -> None:
    test_assets_dir = root_dir / "guns-tests"
    if test_assets_dir.is_dir():
        print("Copying test assets from guns-qa into the GUNS workspace")
        shutil.copytree(test_assets_dir, work_dir, dirs_exist_ok=True)


def expected_test_path(work_dir: Path, test_class: str) -> Path:
    relative_path = Path(*test_class.split(".")).with_suffix(".java")
    return work_dir / "src" / "test" / "java" / relative_path


def portable_maven_command(root_dir: Path, maven_version: str) -> list[str]:
    tools_dir = root_dir / ".tmp" / "tools"
    archive_base = f"apache-maven-{maven_version}-bin"

    if os.name == "nt":
        archive_path = tools_dir / f"{archive_base}.zip"
        extracted_dir = tools_dir / f"apache-maven-{maven_version}"
        executable = extracted_dir / "bin" / "mvn.cmd"
        archive_url = f"https://archive.apache.org/dist/maven/maven-3/{maven_version}/binaries/{archive_base}.zip"
    else:
        archive_path = tools_dir / f"{archive_base}.tar.gz"
        extracted_dir = tools_dir / f"apache-maven-{maven_version}"
        executable = extracted_dir / "bin" / "mvn"
        archive_url = f"https://archive.apache.org/dist/maven/maven-3/{maven_version}/binaries/{archive_base}.tar.gz"

    ensure_dir(tools_dir)
    if not executable.exists():
        print(f"Downloading portable Maven {maven_version}")
        urllib.request.urlretrieve(archive_url, archive_path)
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(tools_dir)
        else:
            with tarfile.open(archive_path, "r:gz") as archive:
                archive.extractall(tools_dir)
    return [str(executable)]


def docker_ready() -> bool:
    docker_binary = shutil.which("docker")
    if not docker_binary:
        return False
    return (
        subprocess.run(
            [docker_binary, "info"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def class_entry_path(class_name: str) -> Path:
    return Path(*class_name.split(".")).with_suffix(".class")


def source_entry_path(class_name: str) -> Path:
    return Path(*class_name.split(".")).with_suffix(".java")


def list_has_files(path: Path) -> bool:
    return path.is_file() or any(candidate.is_file() for candidate in path.rglob("*"))


def copy_class_family_from_directory(source_root: Path, relative_class_path: Path, destination_root: Path) -> list[Path]:
    package_dir = source_root / relative_class_path.parent
    if not package_dir.is_dir():
        return []

    copied_files: list[Path] = []
    stem = relative_class_path.stem
    for candidate in package_dir.iterdir():
        if not candidate.is_file() or candidate.suffix != ".class":
            continue
        if candidate.name != relative_class_path.name and not candidate.name.startswith(f"{stem}$"):
            continue
        target_path = destination_root / relative_class_path.parent / candidate.name
        ensure_dir(target_path.parent)
        shutil.copy2(candidate, target_path)
        copied_files.append(target_path)
    return copied_files


def copy_source_from_directory(source_root: Path, relative_source_path: Path, destination_root: Path) -> bool:
    source_path = source_root / relative_source_path
    if not source_path.is_file():
        return False

    target_path = destination_root / relative_source_path
    ensure_dir(target_path.parent)
    shutil.copy2(source_path, target_path)
    return True


def extract_class_family_from_archive(
    archive_path: Path, relative_class_path: Path, destination_root: Path
) -> list[Path]:
    if not archive_path.is_file():
        return []

    copied_files: list[Path] = []
    entry_name = relative_class_path.as_posix()
    entry_prefix = entry_name[: -len(".class")]
    with zipfile.ZipFile(archive_path, "r") as archive:
        for member in archive.infolist():
            if member.is_dir():
                continue
            if member.filename != entry_name and not (
                member.filename.startswith(f"{entry_prefix}$") and member.filename.endswith(".class")
            ):
                continue
            target_path = destination_root / Path(member.filename)
            ensure_dir(target_path.parent)
            with archive.open(member, "r") as source_handle, target_path.open("wb") as target_handle:
                shutil.copyfileobj(source_handle, target_handle)
            copied_files.append(target_path)
    return copied_files


def extract_source_from_archive(archive_path: Path, relative_source_path: Path, destination_root: Path) -> bool:
    if not archive_path.is_file():
        return False

    entry_name = relative_source_path.as_posix()
    with zipfile.ZipFile(archive_path, "r") as archive:
        try:
            member = archive.getinfo(entry_name)
        except KeyError:
            return False
        target_path = destination_root / relative_source_path
        ensure_dir(target_path.parent)
        with archive.open(member, "r") as source_handle, target_path.open("wb") as target_handle:
            shutil.copyfileobj(source_handle, target_handle)
    return True


def archive_contains_member(archive_path: Path, member_name: str) -> bool:
    if not archive_path.is_file():
        return False
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            archive.getinfo(member_name)
            return True
    except (KeyError, FileNotFoundError, zipfile.BadZipFile):
        return False


def find_class_archive(local_m2_cache: Path, relative_class_path: Path) -> Path | None:
    entry_name = relative_class_path.as_posix()
    for archive_path in sorted(local_m2_cache.rglob("*.jar")):
        archive_name = archive_path.name
        if archive_name.endswith("-sources.jar") or archive_name.endswith("-javadoc.jar"):
            continue
        if archive_contains_member(archive_path, entry_name):
            return archive_path
    return None


def find_source_archive(binary_archive_path: Path, relative_source_path: Path) -> Path | None:
    expected_path = binary_archive_path.with_name(f"{binary_archive_path.stem}-sources.jar")
    if archive_contains_member(expected_path, relative_source_path.as_posix()):
        return expected_path

    for archive_path in sorted(binary_archive_path.parent.glob("*-sources.jar")):
        if archive_contains_member(archive_path, relative_source_path.as_posix()):
            return archive_path
    return None


def ensure_jacoco_cli(root_dir: Path, version: str) -> Path:
    tools_dir = root_dir / ".tmp" / "tools"
    ensure_dir(tools_dir)
    cli_jar_path = tools_dir / f"org.jacoco.cli-{version}-nodeps.jar"
    if cli_jar_path.is_file():
        return cli_jar_path

    urls = [
        f"https://repo.maven.apache.org/maven2/org/jacoco/org.jacoco.cli/{version}/org.jacoco.cli-{version}-nodeps.jar",
        f"https://repo1.maven.org/maven2/org/jacoco/org.jacoco.cli/{version}/org.jacoco.cli-{version}-nodeps.jar",
    ]
    last_error = ""
    for url in urls:
        try:
            print(f"Downloading JaCoCo CLI {version} from {url}")
            urllib.request.urlretrieve(url, cli_jar_path)
            return cli_jar_path
        except Exception as exc:  # pragma: no cover - exercised by runtime download failures
            last_error = f"{exc.__class__.__name__}: {exc}"
    raise RuntimeError(f"Unable to download JaCoCo CLI {version}. {last_error}")


def materialize_coverage_targets(
    work_dir: Path,
    local_m2_cache: Path,
    coverage_classes: list[str],
    classfiles_root: Path,
    sourcefiles_root: Path,
) -> list[str]:
    ensure_dir(classfiles_root)
    ensure_dir(sourcefiles_root)
    resolved_targets: list[str] = []

    for coverage_class in coverage_classes:
        relative_class_path = class_entry_path(coverage_class)
        relative_source_path = source_entry_path(coverage_class)

        copied_from_project = copy_class_family_from_directory(
            work_dir / "target" / "classes", relative_class_path, classfiles_root
        )
        if copied_from_project:
            copy_source_from_directory(work_dir / "src" / "main" / "java", relative_source_path, sourcefiles_root)
            resolved_targets.append(coverage_class)
            continue

        archive_path = find_class_archive(local_m2_cache, relative_class_path)
        if archive_path is None:
            raise RuntimeError(
                f"Unable to find compiled class data for coverage target {coverage_class} in target/classes or {local_m2_cache}."
            )

        copied_from_archive = extract_class_family_from_archive(archive_path, relative_class_path, classfiles_root)
        if not copied_from_archive:
            raise RuntimeError(f"Unable to extract class files for coverage target {coverage_class} from {archive_path}.")

        source_archive_path = find_source_archive(archive_path, relative_source_path)
        if source_archive_path is not None:
            extract_source_from_archive(source_archive_path, relative_source_path, sourcefiles_root)

        resolved_targets.append(coverage_class)

    return resolved_targets


def generate_jacoco_report(
    root_dir: Path,
    work_dir: Path,
    artifact_dir: Path,
    local_m2_cache: Path,
    coverage_classes: list[str],
) -> dict[str, object]:
    exec_path = work_dir / "target" / "jacoco.exec"
    if not exec_path.is_file():
        return {
            "jacoco_status": "missing",
            "jacoco_summary": "JaCoCo exec data was not produced.",
            "jacoco_counters": {},
            "jacoco_report_xml": str((artifact_dir / "jacoco-report" / "jacoco.xml")),
            "jacoco_report_html": str((artifact_dir / "jacoco-report" / "index.html")),
            "jacoco_targets": coverage_classes,
            "jacoco_bundle_name": "",
        }

    report_dir = artifact_dir / "jacoco-report"
    scope_classfiles_dir = artifact_dir / "jacoco-classfiles"
    scope_sourcefiles_dir = artifact_dir / "jacoco-sourcefiles"
    remove_tree(report_dir)
    remove_tree(scope_classfiles_dir)
    remove_tree(scope_sourcefiles_dir)
    ensure_dir(report_dir)

    source_paths: list[Path] = []
    if coverage_classes:
        # When the production class lives in a dependency JAR, report only the mapped target classes.
        resolved_targets = materialize_coverage_targets(
            work_dir=work_dir,
            local_m2_cache=local_m2_cache,
            coverage_classes=coverage_classes,
            classfiles_root=scope_classfiles_dir,
            sourcefiles_root=scope_sourcefiles_dir,
        )
        class_paths = [scope_classfiles_dir]
        if list_has_files(scope_sourcefiles_dir):
            source_paths.append(scope_sourcefiles_dir)
        bundle_name = ", ".join(resolved_targets)
    else:
        classfiles_dir = work_dir / "target" / "classes"
        if not list_has_files(classfiles_dir):
            raise RuntimeError(f"JaCoCo report cannot be generated because {classfiles_dir} is missing.")
        class_paths = [classfiles_dir]
        source_dir = work_dir / "src" / "main" / "java"
        if list_has_files(source_dir):
            source_paths.append(source_dir)
        resolved_targets = []
        bundle_name = "guns"

    cli_jar_path = ensure_jacoco_cli(root_dir, JACOCO_MAVEN_PLUGIN_VERSION)
    xml_path = report_dir / "jacoco.xml"
    csv_path = report_dir / "jacoco.csv"
    command = ["java", "-jar", str(cli_jar_path), "report", str(exec_path)]
    for class_path in class_paths:
        command.extend(["--classfiles", str(class_path)])
    for source_path in source_paths:
        command.extend(["--sourcefiles", str(source_path)])
    command.extend(
        [
            "--html",
            str(report_dir),
            "--xml",
            str(xml_path),
            "--csv",
            str(csv_path),
            "--name",
            bundle_name,
        ]
    )

    if run_command(command, cwd=root_dir) != 0:
        raise RuntimeError("JaCoCo CLI report generation failed.")

    return {
        "jacoco_status": "generated",
        "jacoco_summary": "",
        "jacoco_counters": {},
        "jacoco_report_xml": str(xml_path),
        "jacoco_report_html": str(report_dir / "index.html"),
        "jacoco_targets": resolved_targets,
        "jacoco_bundle_name": bundle_name,
    }


def parse_surefire_reports(report_dir: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "failure_summary": "",
        "report_files": [],
    }

    if not report_dir.is_dir():
        return result

    first_problem = ""
    for xml_path in sorted(report_dir.glob("TEST-*.xml")):
        result["report_files"].append(xml_path.name)
        root = element_tree.parse(xml_path).getroot()
        suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
        for suite in suites:
            result["tests"] += int(suite.attrib.get("tests", 0))
            result["failures"] += int(suite.attrib.get("failures", 0))
            result["errors"] += int(suite.attrib.get("errors", 0))
            result["skipped"] += int(suite.attrib.get("skipped", 0))

            if first_problem:
                continue
            for testcase in suite.findall("testcase"):
                failure = testcase.find("failure")
                if failure is None:
                    failure = testcase.find("error")
                if failure is None:
                    continue
                message = (failure.attrib.get("message") or failure.text or "").strip()
                message = message.splitlines()[0] if message else f"{failure.tag} reported without a message"
                first_problem = (
                    f"{testcase.attrib.get('classname', 'unknown')}#"
                    f"{testcase.attrib.get('name', 'unknown')}: {message}"
                )
                break

    result["failure_summary"] = first_problem
    return result


def format_ratio(covered: int, missed: int) -> str:
    total = covered + missed
    if total <= 0:
        return "n/a"
    return f"{(covered / total) * 100:.2f}%"


def parse_jacoco_report(report_path: Path) -> dict[str, object]:
    result: dict[str, object] = {
        "jacoco_status": "missing",
        "jacoco_summary": "JaCoCo report was not produced.",
        "jacoco_counters": {},
        "jacoco_report_xml": str(report_path),
        "jacoco_report_html": str(report_path.with_name("index.html")),
    }

    if not report_path.is_file():
        return result

    try:
        root = element_tree.parse(report_path).getroot()
        counters: dict[str, dict[str, object]] = {}
        for counter in root.findall("counter"):
            counter_type = str(counter.attrib.get("type", "")).lower()
            covered = int(counter.attrib.get("covered", 0))
            missed = int(counter.attrib.get("missed", 0))
            counters[counter_type] = {
                "covered": covered,
                "missed": missed,
                "total": covered + missed,
                "ratio": format_ratio(covered, missed),
            }

        def counter_ratio(counter_type: str) -> str:
            counter = counters.get(counter_type, {})
            return str(counter.get("ratio", "n/a"))

        result["jacoco_status"] = "collected"
        result["jacoco_counters"] = counters
        result["jacoco_summary"] = (
            f"line {counter_ratio('line')}, "
            f"branch {counter_ratio('branch')}, "
            f"method {counter_ratio('method')}"
        )
    except Exception as exc:  # pragma: no cover - exercised by malformed reports
        result["jacoco_status"] = "parse-failed"
        result["jacoco_summary"] = f"JaCoCo report parsing failed: {exc.__class__.__name__}: {exc}"

    return result


def write_result_files(artifact_dir: Path, metadata: dict[str, object], result: dict[str, object]) -> None:
    metadata_text = "\n".join(
        [
            f"GUNS repo: {metadata['guns_repo_url']}",
            f"Fallback repo: {metadata['guns_fallback_repo_url']}",
            f"Pinned ref: {metadata['guns_ref']}",
            f"Resolved commit: {metadata['resolved_head']}",
            f"Selected test: {metadata['test_class']}",
            f"Coverage targets: {', '.join(metadata['coverage_classes']) or 'project classes'}",
            f"Workspace: {metadata['work_dir']}",
            f"Artifacts: {metadata['artifact_dir']}",
            f"Execution method: {result['execution_method']}",
            f"Result category: {result['category']}",
            f"Failure summary: {result['failure_summary']}",
            f"Test exit code: {result['test_exit_code']}",
            f"JaCoCo status: {result['jacoco_status']}",
            f"JaCoCo bundle: {result['jacoco_bundle_name']}",
            f"JaCoCo targets: {', '.join(result['jacoco_targets']) or 'project classes'}",
            f"JaCoCo summary: {result['jacoco_summary']}",
            f"JaCoCo report xml: {result['jacoco_report_xml']}",
            f"JaCoCo report html: {result['jacoco_report_html']}",
        ]
    )
    run_summary = "\n".join(
        [
            "### Test run result",
            f"- Result category: {result['category']}",
            f"- Failure summary: {result['failure_summary'] or 'none'}",
            f"- Execution method: {result['execution_method']}",
            f"- Selected test: {metadata['test_class']}",
            f"- Resolved commit: {metadata['resolved_head']}",
            (
                f"- JUnit totals: tests={result['tests']} failures={result['failures']} "
                f"errors={result['errors']} skipped={result['skipped']}"
            ),
            f"- JaCoCo status: {result['jacoco_status']}",
            f"- JaCoCo bundle: {result['jacoco_bundle_name'] or 'none'}",
            f"- JaCoCo targets: {', '.join(result['jacoco_targets']) or 'project classes'}",
            f"- JaCoCo summary: {result['jacoco_summary']}",
            f"- Exit code: {result['test_exit_code']}",
            "",
        ]
    )

    write_text(artifact_dir / "run-metadata.txt", metadata_text)
    write_text(artifact_dir / "run-summary.txt", run_summary)
    write_json(artifact_dir / "run-result.json", result)


def main() -> int:
    args = parse_args()
    root_dir = Path(args.root_dir).resolve() if args.root_dir else Path(__file__).resolve().parents[1]
    work_dir = Path(args.guns_work_dir) if args.guns_work_dir else root_dir / ".tmp" / "guns-src"
    artifact_dir = Path(args.guns_artifact_dir) if args.guns_artifact_dir else root_dir / ".artifacts" / "guns"
    local_m2_cache = Path(args.local_m2_cache) if args.local_m2_cache else root_dir / ".tmp" / "m2" / "repository"

    ensure_dir(work_dir.parent)
    ensure_dir(artifact_dir)
    ensure_dir(local_m2_cache)
    remove_tree(work_dir)
    coverage_classes = args.coverage_class or env_list("GUNS_COVERAGE_CLASSES")

    metadata: dict[str, object] = {
        "guns_repo_url": args.guns_repo_url,
        "guns_fallback_repo_url": args.guns_fallback_repo_url,
        "guns_ref": args.guns_ref,
        "resolved_head": "",
        "test_class": args.test_class,
        "coverage_classes": coverage_classes,
        "work_dir": str(work_dir),
        "artifact_dir": str(artifact_dir),
    }
    result: dict[str, object] = {
        "status": "failure",
        "category": "test-infrastructure-failed",
        "failure_summary": "",
        "execution_method": "not-started",
        "test_exit_code": 1,
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "report_files": [],
        "selected_test": args.test_class,
        "resolved_commit": "",
        "pinned_ref": args.guns_ref,
        "jacoco_status": "not-collected",
        "jacoco_summary": "JaCoCo collection has not run.",
        "jacoco_report_xml": "",
        "jacoco_report_html": "",
        "jacoco_counters": {},
        "jacoco_targets": coverage_classes,
        "jacoco_bundle_name": "",
    }

    try:
        if not args.test_class.strip():
            raise RuntimeError("GUNS test class is required. Set GUNS_TEST_CLASS or pass --test-class.")

        clone_repo(work_dir, [args.guns_repo_url, args.guns_fallback_repo_url], args.guns_default_branch)
        resolved_head = resolve_head(work_dir, args.guns_ref)
        metadata["resolved_head"] = resolved_head
        result["resolved_commit"] = resolved_head
        copy_test_assets(root_dir, work_dir)

        selected_test_path = expected_test_path(work_dir, args.test_class)
        if not selected_test_path.is_file():
            raise RuntimeError(f"Expected test asset was not copied into the GUNS workspace: {selected_test_path}")

        if shutil.which("mvn"):
            execution_method = "system-maven"
            command = [
                "mvn",
                "-B",
                "-ntp",
                f"-Dmaven.repo.local={local_m2_cache}",
                "-Dmaven.test.failure.ignore=true",
                "-Djacoco.destFile=target/jacoco.exec",
                f"-Dtest={args.test_class}",
                f"org.jacoco:jacoco-maven-plugin:{JACOCO_MAVEN_PLUGIN_VERSION}:prepare-agent",
                "test",
            ]
        elif docker_ready():
            execution_method = "docker-maven"
            command = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{work_dir}:/workspace",
                "-v",
                f"{local_m2_cache}:/root/.m2/repository",
                "-w",
                "/workspace",
                "maven:3.9.9-eclipse-temurin-17",
                "mvn",
                "-B",
                "-ntp",
                "-Dmaven.test.failure.ignore=true",
                "-Djacoco.destFile=target/jacoco.exec",
                f"-Dtest={args.test_class}",
                f"org.jacoco:jacoco-maven-plugin:{JACOCO_MAVEN_PLUGIN_VERSION}:prepare-agent",
                "test",
            ]
        else:
            execution_method = "portable-maven"
            command = portable_maven_command(root_dir, args.maven_version) + [
                "-B",
                "-ntp",
                f"-Dmaven.repo.local={local_m2_cache}",
                "-Dmaven.test.failure.ignore=true",
                "-Djacoco.destFile=target/jacoco.exec",
                f"-Dtest={args.test_class}",
                f"org.jacoco:jacoco-maven-plugin:{JACOCO_MAVEN_PLUGIN_VERSION}:prepare-agent",
                "test",
            ]

        result["execution_method"] = execution_method
        print(f"Running {args.test_class} against {resolved_head}")
        exit_code = run_command(command, cwd=work_dir)
        result["test_exit_code"] = exit_code

        surefire_dir = work_dir / "target" / "surefire-reports"
        artifact_reports_dir = artifact_dir / "surefire-reports"
        remove_tree(artifact_reports_dir)
        if surefire_dir.is_dir():
            shutil.copytree(surefire_dir, artifact_reports_dir, dirs_exist_ok=True)

        report_stats = parse_surefire_reports(surefire_dir)
        result.update(report_stats)
        result.update(
            generate_jacoco_report(
                root_dir=root_dir,
                work_dir=work_dir,
                artifact_dir=artifact_dir,
                local_m2_cache=local_m2_cache,
                coverage_classes=coverage_classes,
            )
        )
        result.update(parse_jacoco_report(Path(str(result["jacoco_report_xml"]))))
        if int(report_stats["tests"]) > 0 and (
            int(report_stats["failures"]) > 0 or int(report_stats["errors"]) > 0
        ):
            result["status"] = "failure"
            result["category"] = "test-assertion-failed"
            result["failure_summary"] = str(report_stats["failure_summary"] or "JUnit assertions failed.")
        elif exit_code == 0:
            result["status"] = "success"
            result["category"] = "success"
            result["failure_summary"] = ""
        else:
            result["status"] = "failure"
            result["category"] = "test-infrastructure-failed"
            result["failure_summary"] = "The test runner failed before producing JUnit assertions."

    except Exception as exc:  # pragma: no cover - exercised by runtime failures
        result["status"] = "failure"
        result["category"] = "test-infrastructure-failed"
        result["failure_summary"] = f"{exc.__class__.__name__}: {exc}"
        result["stacktrace"] = traceback.format_exc()
    finally:
        write_result_files(artifact_dir, metadata, result)

    if result["category"] == "success":
        print("Run completed successfully.")
        return 0

    print(f"Run completed with category {result['category']}.", file=sys.stderr)
    if result["failure_summary"]:
        print(str(result["failure_summary"]), file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
