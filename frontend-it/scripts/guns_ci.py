#!/usr/bin/env python3
"""Shared helpers for Jira and Xray automation scripts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TEST_CLASS_FIELDS = ["testClass"]
EXECUTION_KEY_FIELDS = ["testExecutionKey"]
BUG_KEY_FIELDS = ["bugKey"]
GUNS_REF_FIELDS = ["gunsRef"]
COVERAGE_CLASS_FIELDS = ["coverageClasses"]

ISSUE_KEY_RE = re.compile(r"(GUNSQA-\d+)", re.IGNORECASE)


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8-sig')


def write_text(path: str | Path, content: str) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    path.write_text(content, encoding='utf-8')


def read_json(path: str | Path, default: Any = None) -> Any:
    path = Path(path)
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write_json(path: str | Path, payload: Any) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def first_non_empty(*values: str) -> str:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def find_issue_key(text: str) -> str:
    if not text:
        return ''
    match = ISSUE_KEY_RE.search(text)
    return match.group(1).upper() if match else ''


def find_issue_key_in_payload(event_path: str) -> str:
    if not event_path:
        return ''
    path = Path(event_path)
    if not path.exists():
        return ''
    payload = read_json(path, default={}) or {}
    serialized = json.dumps(payload, ensure_ascii=False)
    return find_issue_key(serialized)


def is_managed_issue(issue_key: str) -> bool:
    return bool(find_issue_key(issue_key))


def load_mapping(mapping_path: str) -> dict[str, Any]:
    return read_json(mapping_path, default={}) or {}


def load_mapping_entry(mapping_path: str, issue_key: str) -> dict[str, Any]:
    mapping = load_mapping(mapping_path)
    entry = mapping.get(issue_key, {})
    return entry if isinstance(entry, dict) else {}


def mapped_value(entry: dict[str, Any], fields: list[str]) -> str:
    for field in fields:
      value = entry.get(field, '') if isinstance(entry, dict) else ''
      if isinstance(value, str) and value.strip():
        return value.strip()
    return ''


def mapped_values(entry: dict[str, Any], fields: list[str]) -> list[str]:
    for field in fields:
        value = entry.get(field, []) if isinstance(entry, dict) else []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
    return []


def issue_url(base_url: str, issue_key: str) -> str:
    return f"{base_url.rstrip('/')}/browse/{issue_key}" if issue_key else ''


def append_github_key_values(target_path: str, values: dict[str, str]) -> None:
    if not target_path:
        return
    lines = []
    for key, value in values.items():
        safe_value = str(value).replace('\r', ' ').replace('\n', ' ')
        lines.append(f"{key}={safe_value}")
    with open(target_path, 'a', encoding='utf-8') as handle:
        handle.write('\n'.join(lines) + ('\n' if lines else ''))


def parse_metadata_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    result: dict[str, str] = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if ': ' not in line:
            continue
        key, value = line.split(': ', 1)
        result[key.strip()] = value.strip()
    return result
