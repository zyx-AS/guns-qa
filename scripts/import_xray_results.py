#!/usr/bin/env python3
"""Import managed execution results into Xray without creating ad-hoc Test issues."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
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


def metadata_value(metadata_path: Path, key: str) -> str:
    return parse_metadata_file(metadata_path).get(key, "")


def xray_status_for_run(run_category: str) -> str:
    if run_category == "success":
        return "PASSED"
    if run_category == "test-assertion-failed":
        return "FAILED"
    return ""


def build_comment(
    selected_test: str,
    github_run_url: str,
    github_sha: str,
    run_category: str,
    failure_summary: str,
) -> str:
    lines = [
        f"Selected test: {selected_test}",
        f"GitHub run: {github_run_url}",
        f"GitHub commit: {github_sha}",
        f"Result category: {run_category}",
    ]
    if failure_summary:
        lines.append(f"Failure summary: {failure_summary}")
    return "\n".join(lines)


def build_execution_payload(
    execution_issue_key: str,
    source_issue_key: str,
    selected_test: str,
    github_run_url: str,
    github_sha: str,
    run_category: str,
    failure_summary: str,
) -> dict[str, object]:
    return {
        "testExecutionKey": execution_issue_key,
        "tests": [
            {
                "testKey": source_issue_key,
                "status": xray_status_for_run(run_category),
                "comment": build_comment(
                    selected_test=selected_test,
                    github_run_url=github_run_url,
                    github_sha=github_sha,
                    run_category=run_category,
                    failure_summary=failure_summary,
                ),
            }
        ],
    }


def summary_text(result: dict[str, object]) -> str:
    return "\n".join(
        [
            "### Xray import result",
            f"- Result category: {result['category']}",
            f"- Result message: {result['message']}",
            f"- Import mode: {result['import_mode']}",
            f"- Source test issue key: {result['source_issue_key'] or 'none'}",
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
    metadata_path = Path(env_default("RUN_METADATA_PATH", str(artifact_dir / "run-metadata.txt")))
    run_result_path = Path(env_default("RUN_RESULT_PATH", str(artifact_dir / "run-result.json")))
    response_path = artifact_dir / "xray-import-response.json"
    summary_path = artifact_dir / "xray-import-summary.txt"
    result_path = artifact_dir / "xray-result.json"

    artifact_dir.mkdir(parents=True, exist_ok=True)

    xray_base_url = env_default("XRAY_BASE_URL", "https://us.xray.cloud.getxray.app")
    xray_client_id = env_default("XRAY_CLIENT_ID", "")
    xray_client_secret = env_default("XRAY_CLIENT_SECRET", "")
    explicit_issue_key = env_default("XRAY_JIRA_ISSUE_KEY", "")
    explicit_execution_key = env_default("XRAY_TEST_EXECUTION_KEY", "")
    jira_base_url = env_default("JIRA_BASE_URL", "https://jira20260410.atlassian.net")
    github_run_id = env_default("GITHUB_RUN_ID", "local-run")
    github_server_url = env_default("GITHUB_SERVER_URL", "https://github.com")
    github_repository = env_default("GITHUB_REPOSITORY", "zyx-AS/guns-qa")
    github_sha = env_default("GITHUB_SHA", "local-sha")
    github_head_ref = env_default("GITHUB_HEAD_REF", "")
    github_ref_name = env_default("GITHUB_REF_NAME", "")
    github_event_path = env_default("GITHUB_EVENT_PATH", "")
    selected_test = env_default("GUNS_TEST_CLASS", metadata_value(metadata_path, "Selected test") or "unknown-test-class")
    pinned_guns_ref = env_default("GUNS_REF", metadata_value(metadata_path, "Pinned ref") or "unknown-guns-ref")
    import_mode = env_default("XRAY_IMPORT_MODE_RESOLVED", "unknown")

    run_result = read_json(run_result_path, default={}) or {}
    run_category = str(run_result.get("category", "unknown"))
    failure_summary = str(run_result.get("failure_summary", "")).strip()
    source_issue_key = detect_issue_key(explicit_issue_key, github_head_ref, github_ref_name, github_event_path)
    github_run_url = f"{github_server_url}/{github_repository}/actions/runs/{github_run_id}"

    result: dict[str, object] = {
        "status": "skipped",
        "category": "xray-import-skipped",
        "message": "",
        "import_mode": import_mode,
        "source_issue_key": source_issue_key,
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

        if not run_result:
            raise RuntimeError("run-result.json was not produced; refusing to import an undefined test result.")

        if not source_issue_key:
            result["message"] = (
                "Skipping Xray import because there is no Jira Test issue key. "
                "The generic flow refuses to let Xray auto-create method-named Test issues."
            )
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            print(str(result["message"]))
            return 0

        if not explicit_execution_key:
            result["message"] = (
                "Skipping Xray import because there is no stable Xray Test Execution key. "
                "The generic flow no longer creates a new execution automatically."
            )
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            print(str(result["message"]))
            return 0

        xray_status = xray_status_for_run(run_category)
        if not xray_status:
            result["message"] = (
                "Skipping Xray import because the run did not produce a business test result that should be recorded "
                "against a Jira Test."
            )
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            print(str(result["message"]))
            return 0

        payload = build_execution_payload(
            execution_issue_key=explicit_execution_key,
            source_issue_key=source_issue_key,
            selected_test=selected_test,
            github_run_url=github_run_url,
            github_sha=github_sha,
            run_category=run_category,
            failure_summary=failure_summary,
        )

        auth_payload = json.dumps({"client_id": xray_client_id, "client_secret": xray_client_secret}).encode("utf-8")
        token_bytes = http_request(
            url=f"{xray_base_url}/api/v2/authenticate",
            method="POST",
            headers={"Content-Type": "application/json"},
            data=auth_payload,
        )
        auth_token = token_bytes.decode("utf-8").strip().strip('"')

        response_bytes = http_request(
            url=f"{xray_base_url}/api/v2/import/execution",
            method="POST",
            headers={
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )
        response_path.write_bytes(response_bytes)

        result["status"] = "success"
        result["category"] = "xray-import-succeeded"
        result["message"] = "Imported the managed Jira Test result into the existing Xray Test Execution."

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
