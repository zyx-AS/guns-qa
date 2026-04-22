#!/usr/bin/env python3
"""Import JUnit results into Xray and persist a structured result summary."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
import xml.etree.ElementTree as element_tree
from pathlib import Path

from guns_ci import (
    find_issue_key,
    find_issue_key_in_payload,
    first_non_empty,
    issue_url,
    parse_metadata_file,
    read_json,
    write_json,
    write_text,
)


def env_default(name: str, fallback: str) -> str:
    return os.environ.get(name, fallback)


def merge_junit_reports(report_dir: Path, output_path: Path) -> None:
    files = sorted(report_dir.glob("TEST-*.xml"))
    if not files:
        raise RuntimeError(f"No JUnit XML files found in {report_dir}")
    if len(files) == 1:
        shutil.copyfile(files[0], output_path)
        return

    root = element_tree.Element("testsuites")
    for xml_path in files:
        root.append(element_tree.parse(xml_path).getroot())
    element_tree.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)


def detect_issue_key(explicit_issue_key: str, head_ref: str, ref_name: str, event_path: str) -> str:
    return first_non_empty(
        find_issue_key(explicit_issue_key),
        find_issue_key(head_ref),
        find_issue_key(ref_name),
        find_issue_key_in_payload(event_path),
    )


def http_request(url: str, method: str, headers: dict[str, str], data: bytes | None = None) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return response.read()


def build_multipart(parts: list[dict[str, object]]) -> tuple[str, bytes]:
    boundary = f"----guns-qa-{uuid.uuid4().hex}"
    body = bytearray()
    for part in parts:
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        disposition = f'Content-Disposition: form-data; name="{part["name"]}"'
        filename = part.get("filename")
        if filename:
            disposition += f'; filename="{filename}"'
        body.extend(f"{disposition}\r\n".encode("utf-8"))
        body.extend(f'Content-Type: {part["content_type"]}\r\n\r\n'.encode("utf-8"))
        body.extend(part["content"])  # type: ignore[arg-type]
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return boundary, bytes(body)


def metadata_value(metadata_path: Path, key: str) -> str:
    return parse_metadata_file(metadata_path).get(key, "")


def summary_text(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "### Xray import result",
            f"- Result category: {result['category']}",
            f"- Result message: {result['message']}",
            f"- Import mode: {result['import_mode']}",
            f"- Source issue key: {result['source_issue_key'] or 'none'}",
            f"- Execution issue key: {result['execution_issue_key'] or 'none'}",
            f"- Execution issue url: {result['execution_issue_url'] or 'none'}",
            f"- Selected test: {result['selected_test']}",
            f"- Pinned GUNS ref: {result['pinned_guns_ref']}",
            f"- GitHub run: {result['github_run_url']}",
            f"- GitHub commit: {result['github_sha']}",
            "",
        ]
    )


def main() -> int:
    root_dir = Path(__file__).resolve().parents[1]
    artifact_dir = Path(env_default("XRAY_ARTIFACT_DIR", str(root_dir / ".artifacts" / "guns")))
    report_dir = Path(env_default("XRAY_REPORT_DIR", str(artifact_dir / "surefire-reports")))
    metadata_path = Path(env_default("RUN_METADATA_PATH", str(artifact_dir / "run-metadata.txt")))
    run_result_path = Path(env_default("RUN_RESULT_PATH", str(artifact_dir / "run-result.json")))
    response_path = artifact_dir / "xray-import-response.json"
    summary_path = artifact_dir / "xray-import-summary.txt"
    result_path = artifact_dir / "xray-result.json"

    artifact_dir.mkdir(parents=True, exist_ok=True)

    xray_base_url = env_default("XRAY_BASE_URL", "https://us.xray.cloud.getxray.app")
    xray_project_key = env_default("XRAY_PROJECT_KEY", "GUNSQA")
    xray_client_id = env_default("XRAY_CLIENT_ID", "")
    xray_client_secret = env_default("XRAY_CLIENT_SECRET", "")
    explicit_issue_key = env_default("XRAY_JIRA_ISSUE_KEY", "")
    explicit_execution_key = env_default("XRAY_TEST_EXECUTION_KEY", "")
    jira_base_url = env_default("JIRA_BASE_URL", "https://jira20260410.atlassian.net")
    github_run_id = env_default("GITHUB_RUN_ID", "local-run")
    github_run_number = env_default("GITHUB_RUN_NUMBER", "local")
    github_server_url = env_default("GITHUB_SERVER_URL", "https://github.com")
    github_repository = env_default("GITHUB_REPOSITORY", "zyx-AS/guns-qa")
    github_sha = env_default("GITHUB_SHA", "local-sha")
    github_head_ref = env_default("GITHUB_HEAD_REF", "")
    github_ref_name = env_default("GITHUB_REF_NAME", "")
    github_event_path = env_default("GITHUB_EVENT_PATH", "")
    selected_test = env_default("GUNS_TEST_CLASS", metadata_value(metadata_path, "Selected test") or "unknown-test-class")
    pinned_guns_ref = env_default("GUNS_REF", metadata_value(metadata_path, "Pinned ref") or "unknown-guns-ref")
    execution_key_source = env_default("GUNS_TEST_CONTEXT_EXECUTION_KEY_SOURCE", "unknown")
    run_result = read_json(run_result_path, default={}) or {}

    source_issue_key = detect_issue_key(explicit_issue_key, github_head_ref, github_ref_name, github_event_path)
    import_mode = "reuse-existing-execution" if explicit_execution_key else "create-new-execution"
    github_run_url = f"{github_server_url}/{github_repository}/actions/runs/{github_run_id}"

    result: dict[str, object] = {
        "status": "skipped",
        "category": "xray-import-skipped",
        "message": "",
        "import_mode": import_mode,
        "source_issue_key": source_issue_key,
        "execution_key_source": execution_key_source,
        "execution_issue_key": explicit_execution_key,
        "execution_issue_url": issue_url(jira_base_url, explicit_execution_key),
        "selected_test": selected_test,
        "pinned_guns_ref": pinned_guns_ref,
        "github_run_url": github_run_url,
        "github_sha": github_sha,
        "response_path": str(response_path),
    }

    try:
        if not xray_client_id or not xray_client_secret:
            result["message"] = "Skipping Xray import because XRAY_CLIENT_ID / XRAY_CLIENT_SECRET are not configured."
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            print(str(result["message"]))
            return 0

        if not report_dir.is_dir():
            if run_result.get("category") == "test-infrastructure-failed":
                result["message"] = "Skipping Xray import because no JUnit report was produced after the infrastructure failure."
                write_text(summary_path, summary_text(result))
                write_json(result_path, result)
                print(str(result["message"]))
                return 0
            raise RuntimeError(f"JUnit report directory does not exist: {report_dir}")

        if not source_issue_key and not explicit_execution_key:
            result["message"] = "Skipping Xray import because no Jira issue key or explicit execution key was provided."
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            print(str(result["message"]))
            return 0

        with tempfile.TemporaryDirectory() as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            merged_report_path = temp_dir / "junit-report.xml"
            info_path = temp_dir / "info.json"
            test_info_path = temp_dir / "testInfo.json"
            merge_junit_reports(report_dir, merged_report_path)

            summary_label = f"[{source_issue_key}] GUNS unit test CI" if source_issue_key else "GUNS unit test CI"
            info_payload = {
                "fields": {
                    "project": {"key": xray_project_key},
                    "summary": f"{summary_label} / {selected_test} / run {github_run_number}",
                    "description": "\n".join(
                        [
                            f"Source Jira issue: {source_issue_key or 'none'}",
                            f"GitHub run: {github_run_url}",
                            f"GitHub commit: {github_sha}",
                        ]
                    ),
                    "issuetype": {"name": "Test Execution"},
                    "labels": ["guns-qa", "github-actions", "xray-auto-import"],
                }
            }
            test_info_payload = {
                "fields": {
                    "project": {"key": xray_project_key},
                    "issuetype": {"name": "Test"},
                    "labels": ["guns-qa", "automation"],
                }
            }
            info_path.write_text(json.dumps(info_payload, ensure_ascii=False), encoding="utf-8")
            test_info_path.write_text(json.dumps(test_info_payload, ensure_ascii=False), encoding="utf-8")

            auth_payload = json.dumps(
                {"client_id": xray_client_id, "client_secret": xray_client_secret}
            ).encode("utf-8")
            token_bytes = http_request(
                url=f"{xray_base_url}/api/v2/authenticate",
                method="POST",
                headers={"Content-Type": "application/json"},
                data=auth_payload,
            )
            auth_token = token_bytes.decode("utf-8").strip().strip('"')

            if explicit_execution_key:
                response_bytes = http_request(
                    url=(
                        f"{xray_base_url}/api/v2/import/execution/junit?"
                        f"projectKey={urllib.parse.quote(xray_project_key)}&"
                        f"testExecKey={urllib.parse.quote(explicit_execution_key)}"
                    ),
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "Content-Type": "text/xml",
                    },
                    data=merged_report_path.read_bytes(),
                )
                execution_issue_key = explicit_execution_key
            else:
                boundary, body = build_multipart(
                    [
                        {
                            "name": "results",
                            "filename": merged_report_path.name,
                            "content_type": "text/xml",
                            "content": merged_report_path.read_bytes(),
                        },
                        {
                            "name": "info",
                            "filename": info_path.name,
                            "content_type": "application/json",
                            "content": info_path.read_bytes(),
                        },
                        {
                            "name": "testInfo",
                            "filename": test_info_path.name,
                            "content_type": "application/json",
                            "content": test_info_path.read_bytes(),
                        },
                    ]
                )
                response_bytes = http_request(
                    url=f"{xray_base_url}/api/v2/import/execution/junit/multipart",
                    method="POST",
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "Content-Type": f"multipart/form-data; boundary={boundary}",
                    },
                    data=body,
                )
                response_json = json.loads(response_bytes.decode("utf-8"))
                execution_issue_key = str(response_json.get("key", "")).strip()

            response_path.write_bytes(response_bytes)

        result["status"] = "success"
        result["category"] = "xray-import-succeeded"
        result["message"] = "Imported JUnit results into Xray."
        result["execution_issue_key"] = execution_issue_key
        result["execution_issue_url"] = issue_url(jira_base_url, execution_issue_key)

    except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in CI failure paths
        error_body = exc.read().decode("utf-8", errors="replace")
        response_path.write_text(error_body, encoding="utf-8")
        result["status"] = "failure"
        result["category"] = "xray-import-failed"
        result["message"] = f"HTTP {exc.code}: {error_body or exc.reason}"
    except Exception as exc:  # pragma: no cover - exercised in CI failure paths
        result["status"] = "failure"
        result["category"] = "xray-import-failed"
        result["message"] = f"{exc.__class__.__name__}: {exc}"

    write_text(summary_path, summary_text(result))
    write_json(result_path, result)
    print(str(result["message"]))
    return 0 if result["category"] != "xray-import-failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
