#!/usr/bin/env python3
"""Resolve the effective Jira/Xray test context for a workflow run."""

from __future__ import annotations

import argparse
import json
import os
import re
from typing import Any

ISSUE_KEY_PATTERN = re.compile(r"([A-Z][A-Z0-9]+-\d+)")
EXECUTION_KEY_FIELDS = ("testExecutionKey", "executionKey", "xrayTestExecutionKey")
TEST_CLASS_FIELDS = ("testClass", "gunsTestClass")


def first_non_empty(*values: str | None) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def find_issue_key(*candidates: str | None) -> str:
    for candidate in candidates:
        if not candidate:
            continue
        match = ISSUE_KEY_PATTERN.search(candidate)
        if match:
            return match.group(1)
    return ""


def find_issue_key_in_payload(event_path: str) -> str:
    if not event_path or not os.path.isfile(event_path):
        return ""

    with open(event_path, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    direct_candidates = (
        payload.get("head_commit", {}).get("message"),
        payload.get("pull_request", {}).get("title"),
        payload.get("pull_request", {}).get("head", {}).get("ref"),
    )
    issue_key = find_issue_key(*direct_candidates)
    if issue_key:
        return issue_key

    for commit in payload.get("commits", []):
        issue_key = find_issue_key(commit.get("message"))
        if issue_key:
            return issue_key

    return ""


def load_mapping(mapping_path: str, issue_key: str) -> dict[str, Any]:
    if not issue_key or not mapping_path or not os.path.isfile(mapping_path):
        return {}

    with open(mapping_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    entry = data.get(issue_key)
    if isinstance(entry, dict):
        return entry
    if isinstance(entry, str) and entry.strip():
        return {"testExecutionKey": entry.strip()}
    return {}


def mapped_value(entry: dict[str, Any], field_names: tuple[str, ...]) -> str:
    for field_name in field_names:
        value = entry.get(field_name)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def write_env(env_path: str, values: dict[str, str]) -> None:
    if not env_path:
        return
    with open(env_path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def write_step_summary(
    summary_path: str,
    issue_key: str,
    issue_key_source: str,
    test_class: str,
    test_class_source: str,
    execution_key: str,
    execution_key_source: str,
) -> None:
    if not summary_path:
        return

    lines = [
        "### Resolved test context",
        f"- Jira issue: {issue_key or 'none'} ({issue_key_source})",
        f"- Test class: {test_class} ({test_class_source})",
        f"- Xray Test Execution: {execution_key or 'none'} ({execution_key_source})",
        "",
    ]
    with open(summary_path, "a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping-path", default="")
    parser.add_argument("--default-test-class", default="")
    parser.add_argument("--input-test-class", default="")
    parser.add_argument("--input-jira-issue-key", default="")
    parser.add_argument("--input-xray-test-execution-key", default="")
    parser.add_argument("--github-head-ref", default="")
    parser.add_argument("--github-ref-name", default="")
    parser.add_argument("--github-event-path", default="")
    parser.add_argument("--github-env", default="")
    parser.add_argument("--github-step-summary", default="")
    args = parser.parse_args()

    issue_key = first_non_empty(
        find_issue_key(args.input_jira_issue_key),
        find_issue_key(args.github_head_ref),
        find_issue_key(args.github_ref_name),
        find_issue_key_in_payload(args.github_event_path),
    )

    issue_key_source = "none"
    if find_issue_key(args.input_jira_issue_key):
        issue_key_source = "workflow-input"
    elif find_issue_key(args.github_head_ref):
        issue_key_source = "github-head-ref"
    elif find_issue_key(args.github_ref_name):
        issue_key_source = "github-ref-name"
    elif find_issue_key_in_payload(args.github_event_path):
        issue_key_source = "github-event-payload"

    mapping_entry = load_mapping(args.mapping_path, issue_key)

    mapped_test_class = mapped_value(mapping_entry, TEST_CLASS_FIELDS)
    mapped_execution_key = mapped_value(mapping_entry, EXECUTION_KEY_FIELDS)

    test_class = first_non_empty(
        args.input_test_class,
        mapped_test_class,
        args.default_test_class,
    )
    execution_key = first_non_empty(
        args.input_xray_test_execution_key,
        mapped_execution_key,
    )

    test_class_source = "default-test-class"
    if first_non_empty(args.input_test_class):
        test_class_source = "workflow-input"
    elif mapped_test_class:
        test_class_source = "mapping-file"

    execution_key_source = "none"
    if first_non_empty(args.input_xray_test_execution_key):
        execution_key_source = "workflow-input"
    elif mapped_execution_key:
        execution_key_source = "mapping-file"

    values = {
        "XRAY_JIRA_ISSUE_KEY": issue_key,
        "GUNS_TEST_CLASS": test_class,
        "XRAY_TEST_EXECUTION_KEY": execution_key,
        "GUNS_TEST_CONTEXT_ISSUE_KEY_SOURCE": issue_key_source,
        "GUNS_TEST_CONTEXT_TEST_CLASS_SOURCE": test_class_source,
        "GUNS_TEST_CONTEXT_EXECUTION_KEY_SOURCE": execution_key_source,
    }

    write_env(args.github_env, values)
    write_step_summary(
        args.github_step_summary,
        issue_key=issue_key,
        issue_key_source=issue_key_source,
        test_class=test_class,
        test_class_source=test_class_source,
        execution_key=execution_key,
        execution_key_source=execution_key_source,
    )

    print(json.dumps(values, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
