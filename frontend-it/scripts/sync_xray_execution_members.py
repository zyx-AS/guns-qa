#!/usr/bin/env python3
"""Sync mapped Jira Test issues into a stable Xray Test Execution."""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from guns_ci import EXECUTION_KEY_FIELDS, TEST_CLASS_FIELDS, issue_url, is_managed_issue, load_mapping, mapped_value, write_json, write_text


def env_default(name: str, fallback: str) -> str:
    return os.environ.get(name, fallback)


def http_request(url: str, method: str, headers: dict[str, str], data: bytes | None = None) -> bytes:
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        return response.read()


def jira_auth_header(email: str, token: str) -> str:
    auth_value = base64.b64encode(f'{email}:{token}'.encode('utf-8')).decode('ascii')
    return f'Basic {auth_value}'


def jira_issue(base_url: str, email: str, token: str, issue_key: str) -> dict[str, object]:
    encoded_issue_key = urllib.parse.quote(issue_key, safe='')
    response_bytes = http_request(
        f"{base_url.rstrip('/')}/rest/api/3/issue/{encoded_issue_key}?fields=issuetype",
        'GET',
        {'Authorization': jira_auth_header(email, token), 'Accept': 'application/json'},
    )
    return json.loads(response_bytes.decode('utf-8'))


def authenticate_xray(xray_base_url: str, client_id: str, client_secret: str) -> str:
    response_bytes = http_request(
        f"{xray_base_url.rstrip('/')}/api/v2/authenticate",
        'POST',
        {'Content-Type': 'application/json'},
        json.dumps({'client_id': client_id, 'client_secret': client_secret}).encode('utf-8'),
    )
    return response_bytes.decode('utf-8').strip().strip('"')


def graphql_request(xray_base_url: str, auth_token: str, query: str, variables: dict[str, object]) -> dict[str, object]:
    response_bytes = http_request(
        f"{xray_base_url.rstrip('/')}/api/v2/graphql",
        'POST',
        {
            'Authorization': f'Bearer {auth_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
        json.dumps({'query': query, 'variables': variables}, ensure_ascii=False).encode('utf-8'),
    )
    return json.loads(response_bytes.decode('utf-8'))


def mapped_test_keys_for_execution(mapping: dict[str, object], execution_key: str) -> list[str]:
    matched_keys: list[str] = []
    for issue_key, raw_entry in mapping.items():
        if issue_key.startswith('_') or not isinstance(raw_entry, dict):
            continue
        if not is_managed_issue(issue_key):
            continue
        mapped_execution_key = mapped_value(raw_entry, EXECUTION_KEY_FIELDS)
        mapped_test_class = mapped_value(raw_entry, TEST_CLASS_FIELDS)
        if mapped_execution_key == execution_key and mapped_test_class:
            matched_keys.append(issue_key)
    return sorted(set(matched_keys))


def summary_text(result: dict[str, object]) -> str:
    return '\n'.join([
        '### Xray execution membership sync',
        f"- Result category: {result['category']}",
        f"- Result message: {result['message']}",
        f"- Execution issue key: {result['execution_issue_key'] or 'none'}",
        f"- Mapped tests for execution: {', '.join(result.get('mapped_test_keys', [])) or 'none'}",
        '',
    ])


def main() -> int:
    root_dir = Path(__file__).resolve().parents[1]
    artifact_dir = Path(env_default('XRAY_ARTIFACT_DIR', str(root_dir / '.artifacts' / 'guns')))
    artifact_dir.mkdir(parents=True, exist_ok=True)
    summary_path = artifact_dir / 'xray-sync-summary.txt'
    result_path = artifact_dir / 'xray-sync-result.json'
    response_path = artifact_dir / 'xray-sync-response.json'

    jira_base_url = env_default('JIRA_BASE_URL', 'https://jira20260410.atlassian.net')
    jira_user_email = env_default('JIRA_USER_EMAIL', '')
    jira_api_token = env_default('JIRA_API_TOKEN', '')
    xray_base_url = env_default('XRAY_BASE_URL', 'https://us.xray.cloud.getxray.app')
    xray_client_id = env_default('XRAY_CLIENT_ID', '')
    xray_client_secret = env_default('XRAY_CLIENT_SECRET', '')
    execution_issue_key = env_default('XRAY_TEST_EXECUTION_KEY', '').strip()
    source_issue_key = env_default('XRAY_JIRA_ISSUE_KEY', '').strip()
    mapping_path = env_default('XRAY_TEST_EXECUTION_MAP_PATH', str(root_dir / 'config' / 'xray-test-executions.json'))

    result = {
        'status': 'skipped',
        'category': 'xray-sync-skipped',
        'message': '',
        'execution_issue_key': execution_issue_key,
        'execution_issue_url': issue_url(jira_base_url, execution_issue_key),
        'source_issue_key': source_issue_key,
        'mapped_test_keys': [],
        'existing_test_keys': [],
        'added_test_keys': [],
    }

    try:
        if not source_issue_key or not is_managed_issue(source_issue_key):
            result['message'] = 'Skipping Xray execution member sync because there is no managed Jira Test issue key.'
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            return 0
        if not execution_issue_key:
            result['message'] = 'Skipping Xray execution member sync because there is no stable Xray Test Execution key.'
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            return 0
        if not jira_user_email or not jira_api_token or not xray_client_id or not xray_client_secret:
            result['message'] = 'Skipping Xray execution member sync because Jira or Xray credentials are not configured.'
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            return 0

        mapping = load_mapping(mapping_path)
        mapped_test_keys = mapped_test_keys_for_execution(mapping, execution_issue_key)
        result['mapped_test_keys'] = mapped_test_keys
        if not mapped_test_keys:
            result['message'] = f'No mapped Jira Test issues point to {execution_issue_key}; nothing to sync.'
            write_text(summary_path, summary_text(result))
            write_json(result_path, result)
            return 0

        execution_issue = jira_issue(jira_base_url, jira_user_email, jira_api_token, execution_issue_key)
        execution_issue_id = str(execution_issue.get('id', '')).strip()
        xray_token = authenticate_xray(xray_base_url, xray_client_id, xray_client_secret)
        current_response = graphql_request(
            xray_base_url,
            xray_token,
            'query GetExecutionTests($issueId: String!, $limit: Int!) { getTestExecution(issueId: $issueId) { issueId tests(limit: $limit) { total results { issueId } } } }',
            {'issueId': execution_issue_id, 'limit': 100},
        )
        response_path.write_text(json.dumps(current_response, ensure_ascii=False, indent=2), encoding='utf-8')
        if current_response.get('errors'):
            raise RuntimeError(json.dumps(current_response['errors'], ensure_ascii=False))

        current_issue_ids = {
            str(item.get('issueId', '')).strip()
            for item in (((current_response.get('data') or {}).get('getTestExecution') or {}).get('tests') or {}).get('results', [])
            if isinstance(item, dict) and str(item.get('issueId', '')).strip()
        }

        test_issue_ids: dict[str, str] = {}
        for test_issue_key in mapped_test_keys:
            jira_test_issue = jira_issue(jira_base_url, jira_user_email, jira_api_token, test_issue_key)
            test_issue_ids[test_issue_key] = str(jira_test_issue.get('id', '')).strip()

        reverse_test_issue_ids = {issue_id: issue_key for issue_key, issue_id in test_issue_ids.items()}
        missing_issue_ids = [issue_id for issue_id in test_issue_ids.values() if issue_id and issue_id not in current_issue_ids]
        missing_issue_keys = [reverse_test_issue_ids[issue_id] for issue_id in missing_issue_ids]

        if missing_issue_ids:
            mutation_response = graphql_request(
                xray_base_url,
                xray_token,
                'mutation AddTestsToExecution($issueId: String!, $testIssueIds: [String]) { addTestsToTestExecution(issueId: $issueId, testIssueIds: $testIssueIds) { addedTests warning } }',
                {'issueId': execution_issue_id, 'testIssueIds': missing_issue_ids},
            )
            response_path.write_text(json.dumps(mutation_response, ensure_ascii=False, indent=2), encoding='utf-8')
            if mutation_response.get('errors'):
                raise RuntimeError(json.dumps(mutation_response['errors'], ensure_ascii=False))
            result['added_test_keys'] = missing_issue_keys
            result['message'] = f"Synced mapped Jira Tests into {execution_issue_key}: {', '.join(missing_issue_keys)}."
        else:
            result['message'] = f'{execution_issue_key} already contains all mapped Jira Tests for this stable execution.'

        result['status'] = 'success'
        result['category'] = 'xray-sync-succeeded'
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode('utf-8', errors='replace')
        response_path.write_text(error_body, encoding='utf-8')
        result['status'] = 'failure'
        result['category'] = 'xray-sync-failed'
        result['message'] = f'HTTP {exc.code}: {error_body or exc.reason}'
    except Exception as exc:
        result['status'] = 'failure'
        result['category'] = 'xray-sync-failed'
        result['message'] = f'{exc.__class__.__name__}: {exc}'

    write_text(summary_path, summary_text(result))
    write_json(result_path, result)
    return 0 if result['category'] != 'xray-sync-failed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
