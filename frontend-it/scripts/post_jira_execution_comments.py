#!/usr/bin/env python3
"""Optionally post run summaries back to Jira issues."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from guns_ci import read_json, write_json, write_text


def env_default(name: str, fallback: str) -> str:
    return os.environ.get(name, fallback)


def post_comment(base_url: str, email: str, token: str, issue_key: str, body: dict[str, object]) -> dict[str, object]:
    auth_value = base64.b64encode(f'{email}:{token}'.encode('utf-8')).decode('ascii')
    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}/rest/api/3/issue/{issue_key}/comment",
        data=json.dumps({'body': body}, ensure_ascii=False).encode('utf-8'),
        headers={
            'Authorization': f'Basic {auth_value}',
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8',
        },
        method='POST',
    )
    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode('utf-8'))


def adf_document(items: list[str]) -> dict[str, object]:
    return {
        'type': 'doc',
        'version': 1,
        'content': [
            {'type': 'paragraph', 'content': [{'type': 'text', 'text': 'Automated execution evidence'}]},
            {
                'type': 'bulletList',
                'content': [
                    {'type': 'listItem', 'content': [{'type': 'paragraph', 'content': [{'type': 'text', 'text': item}]}]}
                    for item in items
                ],
            },
        ],
    }


def summary_text(result: dict[str, object]) -> str:
    lines = ['### Jira write-back result', f"- Result category: {result['category']}", f"- Result message: {result['message']}"]
    for comment in result.get('comments', []):
        lines.append(f"- Commented issue: {comment['issue_key']} (comment id: {comment.get('comment_id', 'unknown')})")
    lines.append('')
    return '\n'.join(lines)


def main() -> int:
    root_dir = Path(__file__).resolve().parents[1]
    artifact_dir = Path(env_default('XRAY_ARTIFACT_DIR', str(root_dir / '.artifacts' / 'guns')))
    run_result = read_json(artifact_dir / 'run-result.json', default={}) or {}
    xray_result = read_json(artifact_dir / 'xray-result.json', default={}) or {}
    bug_result = read_json(artifact_dir / 'jira-bug-result.json', default={}) or {}
    summary_path = artifact_dir / 'jira-comment-summary.txt'
    result_path = artifact_dir / 'jira-comment-result.json'

    jira_base_url = env_default('JIRA_BASE_URL', 'https://jira20260410.atlassian.net')
    jira_user_email = env_default('JIRA_USER_EMAIL', '')
    jira_api_token = env_default('JIRA_API_TOKEN', '')
    github_run_id = env_default('GITHUB_RUN_ID', 'local-run')
    github_server_url = env_default('GITHUB_SERVER_URL', 'https://github.com')
    github_repository = env_default('GITHUB_REPOSITORY', 'zyx-AS/guns-qa')
    github_sha = env_default('GITHUB_SHA', 'local-sha')
    branch_name = env_default('GITHUB_HEAD_REF', '') or env_default('GITHUB_REF_NAME', '')

    source_issue_key = str(xray_result.get('source_issue_key', '')).strip()
    execution_issue_key = str(xray_result.get('execution_issue_key', '')).strip()
    bug_issue_key = str(bug_result.get('bug_issue_key', '')).strip()
    run_category = str(run_result.get('category', 'unknown')).strip()
    import_category = str(xray_result.get('category', 'unknown')).strip()
    github_run_url = f'{github_server_url}/{github_repository}/actions/runs/{github_run_id}'

    result = {'status': 'skipped', 'category': 'jira-comment-skipped', 'message': '', 'comments': []}
    if not source_issue_key and not execution_issue_key:
        result['message'] = 'Skipping Jira write-back because there is no source issue or execution issue key.'
        write_text(summary_path, summary_text(result))
        write_json(result_path, result)
        return 0
    if not jira_user_email or not jira_api_token:
        result['message'] = 'Skipping Jira write-back because Jira credentials are not configured.'
        write_text(summary_path, summary_text(result))
        write_json(result_path, result)
        return 0

    items = [
        f'Result: {run_category}',
        f'Run: {github_run_url}',
        f'Commit: {github_sha}',
        f'Branch: {branch_name or "none"}',
        f'Execution key: {execution_issue_key or "none"}',
        f'Xray: {import_category}',
    ]
    if bug_issue_key:
        items.append(f'Bug: {bug_issue_key}')

    comment_targets = []
    if source_issue_key and (run_category != 'success' or import_category != 'xray-import-succeeded'):
        comment_targets.append(source_issue_key)
    if execution_issue_key and execution_issue_key != source_issue_key:
        comment_targets.append(execution_issue_key)

    failures: list[str] = []
    posted_comments: list[dict[str, str]] = []
    for issue_key in comment_targets:
        try:
            response = post_comment(jira_base_url, jira_user_email, jira_api_token, issue_key, adf_document(items))
            posted_comments.append({'issue_key': issue_key, 'comment_id': str(response.get('id', ''))})
        except urllib.error.HTTPError as exc:
            error_text = exc.read().decode('utf-8', errors='replace')
            failures.append(f'{issue_key}: HTTP {exc.code}: {error_text or exc.reason}')
        except Exception as exc:
            failures.append(f'{issue_key}: {exc.__class__.__name__}: {exc}')

    result['comments'] = posted_comments
    if failures:
        result['status'] = 'failure'
        result['category'] = 'jira-comment-failed'
        result['message'] = ' '.join(failures)
    else:
        result['status'] = 'success'
        result['category'] = 'jira-comment-succeeded'
        result['message'] = 'Posted Jira execution comments.'

    write_text(summary_path, summary_text(result))
    write_json(result_path, result)
    return 0 if not failures else 1


if __name__ == '__main__':
    raise SystemExit(main())
