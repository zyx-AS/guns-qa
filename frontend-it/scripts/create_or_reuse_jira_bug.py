#!/usr/bin/env python3
"""Create or reuse a Jira Bug for managed assertion failures."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from guns_ci import BUG_KEY_FIELDS, issue_url, load_mapping_entry, mapped_value, read_json, write_json, write_text

ASSERTION_FAILURE_CATEGORY = 'test-assertion-failed'
DEFAULT_BUG_ISSUE_TYPE_ID = '10022'


def env_default(name: str, fallback: str) -> str:
    return os.environ.get(name, fallback)


def auth_header(email: str, token: str) -> str:
    return base64.b64encode(f'{email}:{token}'.encode('utf-8')).decode('ascii')


def jira_request(base_url: str, email: str, token: str, method: str, path: str, payload: dict[str, object] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode('utf-8')
    request = urllib.request.Request(
        url=f"{base_url.rstrip('/')}{path}",
        data=data,
        headers={
            'Authorization': f'Basic {auth_header(email, token)}',
            'Accept': 'application/json',
            'Content-Type': 'application/json; charset=utf-8',
        },
        method=method,
    )
    with urllib.request.urlopen(request) as response:
        body = response.read()
        return None if not body else json.loads(body.decode('utf-8'))


def summary_text(result: dict[str, object]) -> str:
    return '\n'.join([
        '### Jira Bug automation result',
        f"- Result category: {result['category']}",
        f"- Result message: {result['message']}",
        f"- Bug issue key: {result.get('bug_issue_key', '') or 'none'}",
        '',
    ])


def main() -> int:
    root_dir = Path(__file__).resolve().parents[1]
    artifact_dir = Path(env_default('XRAY_ARTIFACT_DIR', str(root_dir / '.artifacts' / 'guns')))
    mapping_path = env_default('XRAY_TEST_EXECUTION_MAP_PATH', str(root_dir / 'config' / 'xray-test-executions.json'))
    run_result = read_json(artifact_dir / 'run-result.json', default={}) or {}
    xray_result = read_json(artifact_dir / 'xray-result.json', default={}) or {}
    context_result = read_json(artifact_dir / 'context-result.json', default={}) or {}
    result_path = artifact_dir / 'jira-bug-result.json'
    summary_path = artifact_dir / 'jira-bug-summary.txt'

    jira_base_url = env_default('JIRA_BASE_URL', 'https://jira20260410.atlassian.net')
    jira_user_email = env_default('JIRA_USER_EMAIL', '')
    jira_api_token = env_default('JIRA_API_TOKEN', '')
    bug_issue_type_id = env_default('JIRA_BUG_ISSUE_TYPE_ID', DEFAULT_BUG_ISSUE_TYPE_ID)

    source_issue_key = str(xray_result.get('source_issue_key', context_result.get('issue_key', ''))).strip()
    execution_issue_key = str(xray_result.get('execution_issue_key', context_result.get('execution_key', ''))).strip()
    run_category = str(run_result.get('category', 'unknown')).strip()
    failure_summary = str(run_result.get('failure_summary', '')).strip() or 'Automated assertion failed.'

    result = {
        'status': 'skipped',
        'category': 'jira-bug-skipped',
        'message': '',
        'mode': 'skipped',
        'source_issue_key': source_issue_key,
        'execution_issue_key': execution_issue_key,
        'execution_issue_url': issue_url(jira_base_url, execution_issue_key),
        'bug_issue_key': '',
        'bug_issue_url': '',
    }

    try:
        if run_category != ASSERTION_FAILURE_CATEGORY:
            result['message'] = 'Skipping Jira Bug automation because the run did not fail with a test assertion.'
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            return 0
        if not source_issue_key or not jira_user_email or not jira_api_token:
            result['message'] = 'Skipping Jira Bug automation because Jira context or credentials are missing.'
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            return 0

        project_key = source_issue_key.split('-', 1)[0]
        mapping_entry = load_mapping_entry(mapping_path, source_issue_key)
        mapped_bug_key = mapped_value(mapping_entry, BUG_KEY_FIELDS)

        if mapped_bug_key:
            result['status'] = 'success'
            result['category'] = 'jira-bug-succeeded'
            result['message'] = 'Reused the mapped Jira Bug.'
            result['mode'] = 'reused-mapped'
            result['bug_issue_key'] = mapped_bug_key
            result['bug_issue_url'] = issue_url(jira_base_url, mapped_bug_key)
        else:
            created_issue = jira_request(
                jira_base_url,
                jira_user_email,
                jira_api_token,
                'POST',
                '/rest/api/3/issue',
                {
                    'fields': {
                        'project': {'key': project_key},
                        'summary': f'Defect to triage - {source_issue_key}',
                        'issuetype': {'id': bug_issue_type_id},
                        'description': {
                            'type': 'doc',
                            'version': 1,
                            'content': [
                                {
                                    'type': 'paragraph',
                                    'content': [{'type': 'text', 'text': f'Source Test: {source_issue_key}'}],
                                },
                                {
                                    'type': 'paragraph',
                                    'content': [{'type': 'text', 'text': f'Execution: {execution_issue_key or "none"}'}],
                                },
                                {
                                    'type': 'paragraph',
                                    'content': [{'type': 'text', 'text': f'Failure summary: {failure_summary}'}],
                                },
                            ],
                        },
                        'labels': ['auto-managed-bug', f'source-test-{source_issue_key.lower()}'],
                    }
                },
            )
            created_key = str((created_issue or {}).get('key', '')).strip()
            result['status'] = 'success'
            result['category'] = 'jira-bug-succeeded'
            result['message'] = 'Created a Jira Bug for the assertion failure.'
            result['mode'] = 'created'
            result['bug_issue_key'] = created_key
            result['bug_issue_url'] = issue_url(jira_base_url, created_key)
    except urllib.error.HTTPError as exc:
        error_text = exc.read().decode('utf-8', errors='replace')
        result['status'] = 'failure'
        result['category'] = 'jira-bug-failed'
        result['message'] = f'HTTP {exc.code}: {error_text or exc.reason}'
    except Exception as exc:
        result['status'] = 'failure'
        result['category'] = 'jira-bug-failed'
        result['message'] = f'{exc.__class__.__name__}: {exc}'

    write_text(summary_path, summary_text(result))
    write_json(result_path, result)
    return 0 if result['category'] != 'jira-bug-failed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
