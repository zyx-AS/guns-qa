#!/usr/bin/env python3
"""Optionally post run summaries back to Jira issues."""

from __future__ import annotations

import argparse
import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from guns_ci import read_json, write_json, write_text


def env_default(name: str, fallback: str) -> str:
    return os.environ.get(name, fallback)


def text_node(value: str) -> dict[str, object]:
    return {"type": "text", "text": value}


def paragraph(value: str) -> dict[str, object]:
    return {"type": "paragraph", "content": [text_node(value)]}


def bullet_list(items: list[str]) -> dict[str, object]:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [paragraph(item)],
            }
            for item in items
        ],
    }


def adf_document(title: str, items: list[str], footer: str | None = None) -> dict[str, object]:
    content: list[dict[str, object]] = [paragraph(title), bullet_list(items)]
    if footer:
        content.append(paragraph(footer))
    return {"type": "doc", "version": 1, "content": content}


def post_comment(base_url: str, email: str, token: str, issue_key: str, body: dict[str, object]) -> dict[str, object]:
    auth_value = base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")
    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment",
        data=json.dumps({"body": body}, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Basic {auth_value}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def build_items(
    branch_name: str,
    github_sha: str,
    github_run_url: str,
    run_category: str,
    import_category: str,
    import_mode: str,
    execution_issue_key: str,
    execution_issue_url: str,
    source_issue_key: str,
    jacoco_summary: str,
    jacoco_artifact_url: str,
) -> list[str]:
    items = [
        f"Result: {run_category}",
        f"Run: {github_run_url}",
        f"Commit: {github_sha}",
        f"Branch: {branch_name or 'none'}",
        f"Execution key: {execution_issue_key or 'none'}",
        f"Xray: {import_category} ({import_mode})",
        f"JaCoCo: {jacoco_summary or 'not collected'}",
    ]
    if jacoco_artifact_url:
        items.append(f"JaCoCo report: {jacoco_artifact_url}")
    if source_issue_key:
        items.append(f"Source Test: {source_issue_key}")
    if execution_issue_url:
        items.append(f"Execution URL: {execution_issue_url}")
    return items


def should_comment_source_issue(run_category: str, import_category: str) -> bool:
    return run_category != "success" or import_category != "xray-import-succeeded"


def summary_text(result: dict[str, object]) -> str:
    lines = [
        "### Jira write-back result",
        f"- Result category: {result['category']}",
        f"- Result message: {result['message']}",
    ]
    for comment in result.get("comments", []):
        lines.append(
            f"- Commented issue: {comment['issue_key']} (comment id: {comment.get('comment_id', 'unknown')})"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[1]
    artifact_dir = Path(env_default("XRAY_ARTIFACT_DIR", str(root_dir / ".artifacts" / "guns")))
    run_result_path = artifact_dir / "run-result.json"
    xray_result_path = artifact_dir / "xray-result.json"
    summary_path = artifact_dir / "jira-comment-summary.txt"
    result_path = artifact_dir / "jira-comment-result.json"

    jira_base_url = env_default("JIRA_BASE_URL", "https://jira20260410.atlassian.net")
    jira_user_email = env_default("JIRA_USER_EMAIL", "")
    jira_api_token = env_default("JIRA_API_TOKEN", "")
    github_sha = env_default("GITHUB_SHA", "local-sha")
    github_run_id = env_default("GITHUB_RUN_ID", "local-run")
    github_server_url = env_default("GITHUB_SERVER_URL", "https://github.com")
    github_repository = env_default("GITHUB_REPOSITORY", "zyx-AS/guns-qa")
    branch_name = env_default("GITHUB_HEAD_REF", "") or env_default("GITHUB_REF_NAME", "")
    jacoco_artifact_url = env_default("JACOCO_ARTIFACT_URL", "").strip()

    run_result = read_json(run_result_path, default={}) or {}
    xray_result = read_json(xray_result_path, default={}) or {}
    github_run_url = f"{github_server_url}/{github_repository}/actions/runs/{github_run_id}"
    source_issue_key = str(xray_result.get("source_issue_key", "")).strip()
    execution_issue_key = str(xray_result.get("execution_issue_key", "")).strip()
    execution_issue_url = str(xray_result.get("execution_issue_url", "")).strip()
    jacoco_summary = str(run_result.get("jacoco_summary", "")).strip()

    result: dict[str, object] = {
        "status": "skipped",
        "category": "jira-comment-skipped",
        "message": "",
        "comments": [],
    }

    if not source_issue_key and not execution_issue_key:
        result["message"] = "Skipping Jira write-back because there is no source issue or execution issue key."
        write_text(summary_path, summary_text(result))
        write_json(result_path, result)
        print(str(result["message"]))
        return 0

    run_category = str(run_result.get("category", "unknown"))
    import_category = str(xray_result.get("category", "unknown"))
    import_mode = str(xray_result.get("import_mode", "unknown"))
    comment_items = build_items(
        branch_name=branch_name,
        github_sha=github_sha,
        github_run_url=github_run_url,
        run_category=run_category,
        import_category=import_category,
        import_mode=import_mode,
        execution_issue_key=execution_issue_key,
        execution_issue_url=execution_issue_url,
        source_issue_key=source_issue_key,
        jacoco_summary=jacoco_summary,
        jacoco_artifact_url=jacoco_artifact_url,
    )

    comment_targets = []
    if source_issue_key and should_comment_source_issue(run_category, import_category):
        comment_targets.append(
            (
                source_issue_key,
                adf_document(
                    title="Automated execution evidence",
                    items=comment_items,
                    footer="Machine evidence only. Keep human-readable defect analysis in a Jira Bug issue.",
                ),
            )
        )
    if execution_issue_key and execution_issue_key != source_issue_key:
        comment_targets.append(
            (
                execution_issue_key,
                adf_document(
                    title="Automated execution evidence",
                    items=comment_items,
                    footer="Machine evidence only. Keep human-readable defect analysis in a Jira Bug issue.",
                ),
            )
        )

    if args.dry_run:
        result["status"] = "success"
        result["category"] = "jira-comment-dry-run"
        result["message"] = "Dry run completed without posting Jira comments."
        result["comments"] = [{"issue_key": issue_key, "comment_id": "dry-run"} for issue_key, _ in comment_targets]
        write_text(summary_path, summary_text(result))
        write_json(result_path, result)
        print(str(result["message"]))
        return 0

    if not jira_user_email or not jira_api_token:
        result["message"] = "Skipping Jira write-back because JIRA_USER_EMAIL / JIRA_API_TOKEN are not configured."
        write_text(summary_path, summary_text(result))
        write_json(result_path, result)
        print(str(result["message"]))
        return 0

    failures: list[str] = []
    posted_comments: list[dict[str, str]] = []
    for issue_key, body in comment_targets:
        try:
            response = post_comment(jira_base_url, jira_user_email, jira_api_token, issue_key, body)
            posted_comments.append({"issue_key": issue_key, "comment_id": str(response.get("id", ""))})
        except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in CI failure paths
            error_text = exc.read().decode("utf-8", errors="replace")
            failures.append(f"{issue_key}: HTTP {exc.code}: {error_text or exc.reason}")
        except Exception as exc:  # pragma: no cover - exercised in CI failure paths
            failures.append(f"{issue_key}: {exc.__class__.__name__}: {exc}")

    result["comments"] = posted_comments
    if failures:
        result["status"] = "failure"
        result["category"] = "jira-comment-failed"
        result["message"] = " ".join(failures)
    else:
        result["status"] = "success"
        result["category"] = "jira-comment-succeeded"
        result["message"] = "Posted Jira execution comments."

    write_text(summary_path, summary_text(result))
    write_json(result_path, result)
    print(str(result["message"]))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
