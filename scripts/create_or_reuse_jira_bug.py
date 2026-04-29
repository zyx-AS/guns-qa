#!/usr/bin/env python3
"""Create or reuse a Jira Bug for managed assertion failures."""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from guns_ci import (
    BUG_KEY_FIELDS,
    issue_url,
    load_mapping_entry,
    mapped_value,
    parse_metadata_file,
    read_json,
    write_json,
    write_text,
)

ASSERTION_FAILURE_CATEGORY = "test-assertion-failed"
DEFAULT_BUG_ISSUE_TYPE_ID = "10022"


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


def auth_header(email: str, token: str) -> str:
    return base64.b64encode(f"{email}:{token}".encode("utf-8")).decode("ascii")


def jira_request(
    base_url: str,
    email: str,
    token: str,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
) -> Any:
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}{path}",
        data=data,
        headers={
            "Authorization": f"Basic {auth_header(email, token)}",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
        },
        method=method,
    )
    with urllib.request.urlopen(request) as response:
        body = response.read()
        if not body:
            return None
        return json.loads(body.decode("utf-8"))


def metadata_value(metadata_path: Path, key: str) -> str:
    return parse_metadata_file(metadata_path).get(key, "")


def search_bug_by_source_label(
    base_url: str,
    email: str,
    token: str,
    project_key: str,
    source_issue_label: str,
    bug_issue_type_id: str,
) -> dict[str, object] | None:
    payload = {
        "jql": f'project = "{project_key}" AND labels = "{source_issue_label}" ORDER BY created DESC',
        "maxResults": 10,
        "fields": ["summary", "labels", "issuelinks", "issuetype", "assignee"],
    }
    response = jira_request(base_url, email, token, "POST", "/rest/api/3/search/jql", payload=payload) or {}
    issues = response.get("issues", [])
    for issue in issues:
        fields = issue.get("fields", {})
        issue_type = fields.get("issuetype", {}) if isinstance(fields, dict) else {}
        if str(issue_type.get("id", "")).strip() == bug_issue_type_id:
            return issue
    return None


def get_issue(
    base_url: str,
    email: str,
    token: str,
    issue_key: str,
    fields: list[str],
) -> dict[str, object]:
    query = urllib.parse.urlencode({"fields": ",".join(fields)})
    response = jira_request(base_url, email, token, "GET", f"/rest/api/3/issue/{issue_key}?{query}")
    return response if isinstance(response, dict) else {}


def existing_link(issue_payload: dict[str, object], other_issue_key: str, link_type_name: str) -> bool:
    fields = issue_payload.get("fields", {})
    issue_links = fields.get("issuelinks", []) if isinstance(fields, dict) else []
    for issue_link in issue_links:
        if not isinstance(issue_link, dict):
            continue
        link_type = issue_link.get("type", {})
        if not isinstance(link_type, dict) or link_type.get("name") != link_type_name:
            continue
        inward_issue = issue_link.get("inwardIssue", {})
        outward_issue = issue_link.get("outwardIssue", {})
        if isinstance(inward_issue, dict) and inward_issue.get("key") == other_issue_key:
            return True
        if isinstance(outward_issue, dict) and outward_issue.get("key") == other_issue_key:
            return True
    return False


def source_label(issue_key: str) -> str:
    return f"source-test-{issue_key.lower()}"


def execution_label(issue_key: str) -> str:
    return f"execution-{issue_key.lower()}"


def normalize_summary(source_summary: str, source_issue_key: str) -> str:
    cleaned = re.sub(r"\s+", " ", source_summary).strip()
    if cleaned:
        return f"Defect to triage - {cleaned}"
    return f"Defect to triage - {source_issue_key}"


def build_bug_description(
    source_issue_key: str,
    source_issue_summary: str,
    execution_issue_key: str,
    github_run_url: str,
    github_sha: str,
    branch_name: str,
    pinned_guns_ref: str,
    selected_test: str,
    run_category: str,
    failure_summary: str,
    import_category: str,
    import_mode: str,
    jacoco_summary: str,
) -> dict[str, object]:
    items = [
        f"Source Test: {source_issue_key} {source_issue_summary}".strip(),
        f"Related Test Execution: {execution_issue_key or 'none'}",
        f"GitHub run: {github_run_url}",
        f"Branch: {branch_name or 'none'}",
        f"Validated commit: {github_sha}",
        f"Tested GUNS ref: {pinned_guns_ref or 'none'}",
        f"Test class: {selected_test or 'none'}",
        f"Automation result: {run_category}",
        f"Failure summary: {failure_summary or 'none'}",
        f"Xray import: {import_category} ({import_mode})",
        f"JaCoCo: {jacoco_summary or 'not collected'}",
    ]
    return adf_document(
        title="Automatically created Bug placeholder",
        items=items,
        footer="This issue was created by automation. Add readable analysis, root cause, fix notes, and business impact here.",
    )


def build_bug_comment(
    source_issue_key: str,
    execution_issue_key: str,
    github_run_url: str,
    github_sha: str,
    branch_name: str,
    run_category: str,
    failure_summary: str,
    import_category: str,
    import_mode: str,
    jacoco_summary: str,
) -> dict[str, object]:
    items = [
        f"Result: {run_category}",
        f"Failure summary: {failure_summary or 'none'}",
        f"Run: {github_run_url}",
        f"Commit: {github_sha}",
        f"Branch: {branch_name or 'none'}",
        f"Source Test: {source_issue_key or 'none'}",
        f"Execution key: {execution_issue_key or 'none'}",
        f"Xray: {import_category} ({import_mode})",
        f"JaCoCo: {jacoco_summary or 'not collected'}",
    ]
    return adf_document(
        title="Automated defect evidence",
        items=items,
        footer="Short machine evidence only. Keep readable defect analysis in the issue description and follow-up comments.",
    )


def ensure_labels(
    base_url: str,
    email: str,
    token: str,
    bug_issue_key: str,
    issue_payload: dict[str, object],
    labels_to_add: list[str],
) -> list[str]:
    fields = issue_payload.get("fields", {})
    existing = fields.get("labels", []) if isinstance(fields, dict) else []
    existing_labels = [str(label).strip() for label in existing if str(label).strip()]
    merged = sorted(set(existing_labels) | set(labels_to_add))
    if merged != existing_labels:
        jira_request(
            base_url,
            email,
            token,
            "PUT",
            f"/rest/api/3/issue/{bug_issue_key}",
            payload={"fields": {"labels": merged}},
        )
    return merged


def ensure_issue_link(
    base_url: str,
    email: str,
    token: str,
    link_type_name: str,
    inward_issue_key: str,
    outward_issue_key: str,
) -> None:
    jira_request(
        base_url,
        email,
        token,
        "POST",
        "/rest/api/3/issueLink",
        payload={
            "type": {"name": link_type_name},
            "inwardIssue": {"key": inward_issue_key},
            "outwardIssue": {"key": outward_issue_key},
        },
    )


def post_comment(
    base_url: str,
    email: str,
    token: str,
    issue_key: str,
    body: dict[str, object],
) -> dict[str, object]:
    response = jira_request(
        base_url,
        email,
        token,
        "POST",
        f"/rest/api/3/issue/{issue_key}/comment",
        payload={"body": body},
    )
    return response if isinstance(response, dict) else {}


def summary_text(result: dict[str, object]) -> str:
    lines = [
        "### Jira Bug automation result",
        f"- Result category: {result['category']}",
        f"- Result message: {result['message']}",
        f"- Mode: {result.get('mode', 'none')}",
        f"- Source Test issue key: {result.get('source_issue_key', '') or 'none'}",
        f"- Execution issue key: {result.get('execution_issue_key', '') or 'none'}",
        f"- Bug issue key: {result.get('bug_issue_key', '') or 'none'}",
        f"- Bug issue url: {result.get('bug_issue_url', '') or 'none'}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[1]
    artifact_dir = Path(env_default("XRAY_ARTIFACT_DIR", str(root_dir / ".artifacts" / "guns")))
    mapping_path = env_default("XRAY_TEST_EXECUTION_MAP_PATH", str(root_dir / "config" / "xray-test-executions.json"))
    run_result_path = artifact_dir / "run-result.json"
    xray_result_path = artifact_dir / "xray-result.json"
    context_result_path = artifact_dir / "context-result.json"
    metadata_path = artifact_dir / "run-metadata.txt"
    result_path = artifact_dir / "jira-bug-result.json"
    summary_path = artifact_dir / "jira-bug-summary.txt"

    jira_base_url = env_default("JIRA_BASE_URL", "https://jira20260410.atlassian.net")
    jira_user_email = env_default("JIRA_USER_EMAIL", "")
    jira_api_token = env_default("JIRA_API_TOKEN", "")
    github_sha = env_default("GITHUB_SHA", "local-sha")
    github_run_id = env_default("GITHUB_RUN_ID", "local-run")
    github_server_url = env_default("GITHUB_SERVER_URL", "https://github.com")
    github_repository = env_default("GITHUB_REPOSITORY", "zyx-AS/guns-qa")
    branch_name = env_default("GITHUB_HEAD_REF", "") or env_default("GITHUB_REF_NAME", "")
    bug_issue_type_id = env_default("JIRA_BUG_ISSUE_TYPE_ID", DEFAULT_BUG_ISSUE_TYPE_ID)

    artifact_dir.mkdir(parents=True, exist_ok=True)

    run_result = read_json(run_result_path, default={}) or {}
    xray_result = read_json(xray_result_path, default={}) or {}
    context_result = read_json(context_result_path, default={}) or {}
    github_run_url = f"{github_server_url}/{github_repository}/actions/runs/{github_run_id}"

    run_category = str(run_result.get("category", "unknown")).strip()
    failure_summary = str(run_result.get("failure_summary", "")).strip()
    jacoco_summary = str(run_result.get("jacoco_summary", "")).strip()
    import_category = str(xray_result.get("category", "unknown")).strip()
    import_mode = str(xray_result.get("import_mode", context_result.get("import_mode", "unknown"))).strip()
    source_issue_key = str(xray_result.get("source_issue_key", context_result.get("issue_key", ""))).strip()
    execution_issue_key = str(
        xray_result.get("execution_issue_key", context_result.get("execution_key", ""))
    ).strip()
    execution_issue_url = str(
        xray_result.get("execution_issue_url", issue_url(jira_base_url, execution_issue_key))
    ).strip()
    selected_test = str(
        run_result.get(
            "selected_test",
            metadata_value(metadata_path, "Selected test") or context_result.get("test_class", ""),
        )
    ).strip()
    pinned_guns_ref = str(
        run_result.get(
            "pinned_ref",
            metadata_value(metadata_path, "Pinned ref") or context_result.get("guns_ref", ""),
        )
    ).strip()

    result: dict[str, object] = {
        "status": "skipped",
        "category": "jira-bug-skipped",
        "message": "",
        "mode": "skipped",
        "source_issue_key": source_issue_key,
        "execution_issue_key": execution_issue_key,
        "execution_issue_url": execution_issue_url,
        "bug_issue_key": "",
        "bug_issue_url": "",
        "github_run_url": github_run_url,
        "github_sha": github_sha,
    }

    try:
        if run_category != ASSERTION_FAILURE_CATEGORY:
            result["message"] = "Skipping Jira Bug automation because the run did not fail with a test assertion."
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            print(str(result["message"]))
            return 0

        if not source_issue_key:
            raise RuntimeError("Managed assertion failure has no Jira Test issue key; refusing to continue.")

        if not jira_user_email or not jira_api_token:
            raise RuntimeError("JIRA_USER_EMAIL / JIRA_API_TOKEN are required for Bug automation.")

        project_key = source_issue_key.split("-", 1)[0]
        mapping_entry = load_mapping_entry(mapping_path, source_issue_key)
        mapped_bug_key = mapped_value(mapping_entry, BUG_KEY_FIELDS)
        source_issue = get_issue(
            jira_base_url,
            jira_user_email,
            jira_api_token,
            source_issue_key,
            ["summary", "labels", "assignee", "issuelinks"],
        )
        source_fields = source_issue.get("fields", {})
        source_issue_summary = str(source_fields.get("summary", "")).strip()
        source_issue_labels = [
            str(label).strip() for label in source_fields.get("labels", []) if str(label).strip()
        ]
        assignee = source_fields.get("assignee", {})
        assignee_account_id = ""
        if isinstance(assignee, dict):
            assignee_account_id = str(assignee.get("accountId", "")).strip()

        canonical_labels = sorted(
            set(source_issue_labels)
            | {"auto-managed-bug", "defect", source_label(source_issue_key)}
            | ({execution_label(execution_issue_key)} if execution_issue_key else set())
        )

        bug_issue_payload: dict[str, object] | None = None
        mode = ""
        if mapped_bug_key:
            try:
                bug_issue_payload = get_issue(
                    jira_base_url,
                    jira_user_email,
                    jira_api_token,
                    mapped_bug_key,
                    ["summary", "labels", "issuelinks", "issuetype", "assignee"],
                )
                mode = "reused-mapped"
            except urllib.error.HTTPError as exc:
                if exc.code != 404:
                    raise

        if bug_issue_payload is None:
            searched_bug = search_bug_by_source_label(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                project_key,
                source_label(source_issue_key),
                bug_issue_type_id,
            )
            if searched_bug:
                bug_issue_payload = searched_bug
                mode = "reused-searched"

        if bug_issue_payload is None:
            bug_summary = normalize_summary(source_issue_summary, source_issue_key)
            create_payload: dict[str, object] = {
                "fields": {
                    "project": {"key": project_key},
                    "summary": bug_summary,
                    "issuetype": {"id": bug_issue_type_id},
                    "description": build_bug_description(
                        source_issue_key=source_issue_key,
                        source_issue_summary=source_issue_summary,
                        execution_issue_key=execution_issue_key,
                        github_run_url=github_run_url,
                        github_sha=github_sha,
                        branch_name=branch_name,
                        pinned_guns_ref=pinned_guns_ref,
                        selected_test=selected_test,
                        run_category=run_category,
                        failure_summary=failure_summary,
                        import_category=import_category,
                        import_mode=import_mode,
                        jacoco_summary=jacoco_summary,
                    ),
                    "labels": canonical_labels,
                }
            }
            if assignee_account_id:
                create_payload["fields"]["assignee"] = {"accountId": assignee_account_id}
            created_issue = jira_request(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                "POST",
                "/rest/api/3/issue",
                payload=create_payload,
            )
            if not isinstance(created_issue, dict) or not created_issue.get("key"):
                raise RuntimeError("Jira did not return a created Bug issue key.")
            created_bug_key = str(created_issue.get("key", "")).strip()
            bug_issue_payload = get_issue(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                created_bug_key,
                ["summary", "labels", "issuelinks", "issuetype", "assignee"],
            )
            mode = "created"

        bug_issue_key = str(bug_issue_payload.get("key", "")).strip()
        if not bug_issue_key:
            raise RuntimeError("Resolved Bug issue payload does not include a Jira key.")

        merged_labels = ensure_labels(
            jira_base_url,
            jira_user_email,
            jira_api_token,
            bug_issue_key,
            bug_issue_payload,
            canonical_labels,
        )
        bug_issue_payload = get_issue(
            jira_base_url,
            jira_user_email,
            jira_api_token,
            bug_issue_key,
            ["summary", "labels", "issuelinks", "issuetype", "assignee"],
        )

        if not existing_link(bug_issue_payload, source_issue_key, "Defect"):
            ensure_issue_link(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                "Defect",
                inward_issue_key=bug_issue_key,
                outward_issue_key=source_issue_key,
            )
            bug_issue_payload = get_issue(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                bug_issue_key,
                ["summary", "labels", "issuelinks", "issuetype", "assignee"],
            )

        if execution_issue_key and not existing_link(bug_issue_payload, execution_issue_key, "Relates"):
            ensure_issue_link(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                "Relates",
                inward_issue_key=bug_issue_key,
                outward_issue_key=execution_issue_key,
            )

        comment_body = build_bug_comment(
            source_issue_key=source_issue_key,
            execution_issue_key=execution_issue_key,
            github_run_url=github_run_url,
            github_sha=github_sha,
            branch_name=branch_name,
            run_category=run_category,
            failure_summary=failure_summary,
            import_category=import_category,
            import_mode=import_mode,
            jacoco_summary=jacoco_summary,
        )

        if args.dry_run:
            comment_response = {"id": "dry-run"}
            mode = f"{mode}-dry-run" if mode else "dry-run"
        else:
            comment_response = post_comment(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                bug_issue_key,
                comment_body,
            )

        result["status"] = "success"
        result["category"] = "jira-bug-succeeded"
        result["message"] = "Created or reused the Jira Bug and posted execution evidence."
        result["mode"] = mode or "reused"
        result["bug_issue_key"] = bug_issue_key
        result["bug_issue_url"] = issue_url(jira_base_url, bug_issue_key)
        result["bug_comment_id"] = str(comment_response.get("id", "")).strip()
        result["labels"] = merged_labels

    except urllib.error.HTTPError as exc:  # pragma: no cover - exercised in CI failure paths
        error_text = exc.read().decode("utf-8", errors="replace")
        result["status"] = "failure"
        result["category"] = "jira-bug-failed"
        result["message"] = f"HTTP {exc.code}: {error_text or exc.reason}"
    except Exception as exc:  # pragma: no cover - exercised in CI failure paths
        result["status"] = "failure"
        result["category"] = "jira-bug-failed"
        result["message"] = f"{exc.__class__.__name__}: {exc}"

    write_text(summary_path, summary_text(result))
    write_json(result_path, result)
    print(str(result["message"]))
    return 0 if result["category"] != "jira-bug-failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
