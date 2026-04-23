#!/usr/bin/env python3
"""Resolve the effective Jira/Xray test context for a workflow run."""

from __future__ import annotations

import argparse
import json
import sys

from guns_ci import (
    COVERAGE_CLASS_FIELDS,
    EXECUTION_KEY_FIELDS,
    GUNS_REF_FIELDS,
    TEST_CLASS_FIELDS,
    append_github_key_values,
    find_issue_key,
    find_issue_key_in_payload,
    first_non_empty,
    is_managed_issue,
    load_mapping_entry,
    mapped_value,
    mapped_values,
    write_json,
    write_text,
)


def write_step_summary(summary_path: str, context: dict[str, str]) -> None:
    if not summary_path:
        return

    lines = [
        "### Resolved test context",
        f"- Resolved Jira key: {context['issue_key'] or 'none'} ({context['issue_key_source']})",
        f"- Resolved test class: {context['test_class'] or 'none'} ({context['test_class_source']})",
        f"- Resolved execution key: {context['execution_key'] or 'none'} ({context['execution_key_source']})",
        f"- Resolved GUNS ref: {context['guns_ref'] or 'none'} ({context['guns_ref_source']})",
        (
            f"- Resolved coverage classes: {', '.join(context['coverage_classes']) or 'none'} "
            f"({context['coverage_classes_source']})"
        ),
        f"- Import mode: {context['import_mode']}",
        f"- Validation status: {context['validation_status']}",
        f"- Validation message: {context['validation_message']}",
        "",
    ]
    write_text(summary_path, "\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping-path", default="")
    parser.add_argument("--default-guns-ref", default="")
    parser.add_argument("--input-test-class", default="")
    parser.add_argument("--input-guns-ref", default="")
    parser.add_argument("--input-jira-issue-key", default="")
    parser.add_argument("--input-xray-test-execution-key", default="")
    parser.add_argument("--github-head-ref", default="")
    parser.add_argument("--github-ref-name", default="")
    parser.add_argument("--github-event-path", default="")
    parser.add_argument("--github-env", default="")
    parser.add_argument("--github-output", default="")
    parser.add_argument("--github-step-summary", default="")
    parser.add_argument("--context-json-path", default="")
    parser.add_argument("--context-summary-path", default="")
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

    mapping_entry = load_mapping_entry(args.mapping_path, issue_key)
    managed_issue = is_managed_issue(issue_key)
    mapped_test_class = mapped_value(mapping_entry, TEST_CLASS_FIELDS)
    mapped_execution_key = mapped_value(mapping_entry, EXECUTION_KEY_FIELDS)
    mapped_guns_ref = mapped_value(mapping_entry, GUNS_REF_FIELDS)
    mapped_coverage_classes = mapped_values(mapping_entry, COVERAGE_CLASS_FIELDS)

    validation_errors: list[str] = []
    if managed_issue:
        if not mapping_entry:
            validation_errors.append(
                f"Missing mapping entry for managed Jira issue {issue_key} in {args.mapping_path}."
            )
        if not mapped_test_class:
            validation_errors.append(
                f"Managed Jira issue {issue_key} must declare testClass in {args.mapping_path}."
            )
        if not mapped_execution_key:
            validation_errors.append(
                f"Managed Jira issue {issue_key} must declare testExecutionKey in {args.mapping_path}."
            )
    elif not first_non_empty(args.input_test_class, mapped_test_class):
        validation_errors.append(
            "Non-managed runs must provide test_class explicitly; the workflow no longer falls back to a default test."
        )

    if managed_issue:
        test_class = mapped_test_class
        execution_key = mapped_execution_key
        test_class_source = "mapping-file"
        execution_key_source = "mapping-file"
    else:
        test_class = first_non_empty(args.input_test_class, mapped_test_class)
        execution_key = first_non_empty(args.input_xray_test_execution_key, mapped_execution_key)
        test_class_source = "none"
        if first_non_empty(args.input_test_class):
            test_class_source = "workflow-input"
        elif mapped_test_class:
            test_class_source = "mapping-file"
        execution_key_source = "none"
        if first_non_empty(args.input_xray_test_execution_key):
            execution_key_source = "workflow-input"
        elif mapped_execution_key:
            execution_key_source = "mapping-file"

    guns_ref = first_non_empty(args.input_guns_ref, mapped_guns_ref, args.default_guns_ref)
    guns_ref_source = "default-guns-ref"
    if first_non_empty(args.input_guns_ref):
        guns_ref_source = "workflow-input"
    elif mapped_guns_ref:
        guns_ref_source = "mapping-file"

    coverage_classes = mapped_coverage_classes
    coverage_classes_source = "mapping-file" if mapped_coverage_classes else "none"

    import_mode = "skipped-no-jira-context"
    if execution_key and issue_key:
        import_mode = "reuse-existing-execution"
    elif issue_key:
        import_mode = "skipped-missing-execution-key"
    elif execution_key:
        import_mode = "skipped-no-source-test-issue"

    validation_status = "success" if not validation_errors else "failure"
    validation_message = "mapping entry ready" if not validation_errors else " ".join(validation_errors)

    context = {
        "issue_key": issue_key,
        "issue_key_source": issue_key_source,
        "test_class": test_class,
        "test_class_source": test_class_source,
        "execution_key": execution_key,
        "execution_key_source": execution_key_source,
        "guns_ref": guns_ref,
        "guns_ref_source": guns_ref_source,
        "coverage_classes": coverage_classes,
        "coverage_classes_source": coverage_classes_source,
        "import_mode": import_mode,
        "validation_status": validation_status,
        "validation_message": validation_message,
        "managed_issue": "true" if managed_issue else "false",
        "category": "context-resolution-succeeded" if not validation_errors else "context-resolution-failed",
    }

    values = {
        "XRAY_JIRA_ISSUE_KEY": issue_key,
        "GUNS_TEST_CLASS": test_class,
        "XRAY_TEST_EXECUTION_KEY": execution_key,
        "GUNS_REF": guns_ref,
        "GUNS_TEST_CONTEXT_ISSUE_KEY_SOURCE": issue_key_source,
        "GUNS_TEST_CONTEXT_TEST_CLASS_SOURCE": test_class_source,
        "GUNS_TEST_CONTEXT_EXECUTION_KEY_SOURCE": execution_key_source,
        "GUNS_TEST_CONTEXT_GUNS_REF_SOURCE": guns_ref_source,
        "GUNS_TEST_CONTEXT_VALIDATION_STATUS": validation_status,
        "GUNS_TEST_CONTEXT_VALIDATION_MESSAGE": validation_message,
        "GUNS_TEST_CONTEXT_MANAGED_ISSUE": context["managed_issue"],
        "GUNS_COVERAGE_CLASSES": json.dumps(coverage_classes, ensure_ascii=False),
        "XRAY_IMPORT_MODE_RESOLVED": import_mode,
    }

    outputs = {
        "jira_issue_key": issue_key,
        "test_class": test_class,
        "xray_test_execution_key": execution_key,
        "guns_ref": guns_ref,
        "coverage_classes": json.dumps(coverage_classes, ensure_ascii=False),
        "validation_status": validation_status,
        "validation_message": validation_message,
        "category": context["category"],
        "managed_issue": context["managed_issue"],
        "resolved_import_mode": import_mode,
    }

    if args.context_json_path:
        write_json(args.context_json_path, context)
    if args.context_summary_path:
        write_step_summary(args.context_summary_path, context)
    if args.github_step_summary:
        write_step_summary(args.github_step_summary, context)

    append_github_key_values(args.github_env, values)
    append_github_key_values(args.github_output, outputs)

    print(json.dumps(context, ensure_ascii=False, indent=2))
    if validation_errors:
        print(validation_message, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
