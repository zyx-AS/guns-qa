#!/usr/bin/env python3
"""Shared helpers for the GUNS QA automation scripts."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

ISSUE_KEY_PATTERN = re.compile(r"([A-Z][A-Z0-9]+-\d+)")
EXECUTION_KEY_FIELDS = ("testExecutionKey", "executionKey", "xrayTestExecutionKey")
TEST_CLASS_FIELDS = ("testClass", "gunsTestClass")
GUNS_REF_FIELDS = ("gunsRef", "ref", "gunsCommit", "sourceRef")
COVERAGE_CLASS_FIELDS = ("coverageClasses", "coverageClass", "jacocoClasses")
MANAGED_ISSUE_PREFIXES = ("GUNSQA-",)


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

    issue_key = find_issue_key(
        payload.get("head_commit", {}).get("message"),
        payload.get("pull_request", {}).get("title"),
        payload.get("pull_request", {}).get("head", {}).get("ref"),
    )
    if issue_key:
        return issue_key

    for commit in payload.get("commits", []):
        issue_key = find_issue_key(commit.get("message"))
        if issue_key:
            return issue_key

    return ""


def is_managed_issue(issue_key: str, prefixes: tuple[str, ...] = MANAGED_ISSUE_PREFIXES) -> bool:
    return bool(issue_key) and any(issue_key.startswith(prefix) for prefix in prefixes)


def load_mapping(mapping_path: str) -> dict[str, Any]:
    if not mapping_path or not os.path.isfile(mapping_path):
        return {}

    with open(mapping_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    return data if isinstance(data, dict) else {}


def load_mapping_entry(mapping_path: str, issue_key: str) -> dict[str, Any]:
    if not issue_key:
        return {}

    entry = load_mapping(mapping_path).get(issue_key)
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


def mapped_values(entry: dict[str, Any], field_names: tuple[str, ...]) -> list[str]:
    for field_name in field_names:
        value = entry.get(field_name)
        if isinstance(value, str) and value.strip():
            return [value.strip()]
        if isinstance(value, list):
            items = [str(item).strip() for item in value if str(item).strip()]
            if items:
                return items
    return []


def ensure_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.mkdir(parents=True, exist_ok=True)
    return resolved


def ensure_parent(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


def write_json(path: str | Path, payload: Any) -> None:
    resolved = ensure_parent(path)
    with resolved.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def read_json(path: str | Path, default: Any = None) -> Any:
    resolved = Path(path)
    if not resolved.exists():
        return default
    with resolved.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_text(path: str | Path, content: str) -> None:
    resolved = ensure_parent(path)
    resolved.write_text(content, encoding="utf-8")


def append_github_key_values(path: str, values: dict[str, str]) -> None:
    if not path:
        return
    ensure_parent(path)
    with open(path, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def issue_url(base_url: str, issue_key: str) -> str:
    if not base_url or not issue_key:
        return ""
    return f"{base_url.rstrip('/')}/browse/{issue_key}"


def parse_metadata_file(path: str | Path) -> dict[str, str]:
    resolved = Path(path)
    values: dict[str, str] = {}
    if not resolved.exists():
        return values

    for line in resolved.read_text(encoding="utf-8").splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        values[key] = value
    return values
