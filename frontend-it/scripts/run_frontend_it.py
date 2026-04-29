#!/usr/bin/env python3
"""Run the selected Playwright integration test and classify the result."""

from __future__ import annotations

import os
import subprocess
import traceback
import xml.etree.ElementTree as ET
from pathlib import Path

from guns_ci import ensure_dir, write_json, write_text


def env(name: str, fallback: str = '') -> str:
    return os.environ.get(name, fallback)


def run_command(command: list[str], cwd: Path | None = None) -> int:
    return subprocess.run(command, cwd=str(cwd) if cwd else None, check=False).returncode


def parse_junit(report_path: Path) -> dict[str, object]:
    result = {
        'tests': 0,
        'failures': 0,
        'errors': 0,
        'skipped': 0,
        'failure_summary': '',
    }
    if not report_path.exists():
        return result

    root = ET.parse(report_path).getroot()
    suites = [root] if root.tag == 'testsuite' else list(root.findall('testsuite'))
    first_problem = ''
    for suite in suites:
        result['tests'] += int(suite.attrib.get('tests', 0))
        result['failures'] += int(suite.attrib.get('failures', 0))
        result['errors'] += int(suite.attrib.get('errors', 0))
        result['skipped'] += int(suite.attrib.get('skipped', 0))
        if first_problem:
            continue
        for testcase in suite.findall('testcase'):
            failure = testcase.find('failure') or testcase.find('error')
            if failure is None:
                continue
            message = (failure.attrib.get('message') or failure.text or '').strip()
            message = message.splitlines()[0] if message else 'Playwright assertion failed.'
            first_problem = f"{testcase.attrib.get('classname', 'unknown')}#{testcase.attrib.get('name', 'unknown')}: {message}"
            break
    result['failure_summary'] = first_problem
    return result


def main() -> int:
    root_dir = Path(__file__).resolve().parents[1]
    artifact_dir = Path(env('XRAY_ARTIFACT_DIR', str(root_dir / '.artifacts' / 'guns')))
    report_dir = artifact_dir / 'playwright'
    junit_path = report_dir / 'junit.xml'
    html_dir = report_dir / 'html-report'
    ensure_dir(report_dir)

    selector = env('TEST_CLASS_SELECTOR', '').strip()
    result = {
        'status': 'failure',
        'category': 'test-infrastructure-failed',
        'failure_summary': '',
        'execution_method': 'playwright',
        'test_exit_code': 1,
        'tests': 0,
        'failures': 0,
        'errors': 0,
        'skipped': 0,
        'selected_test': selector,
        'report_files': [str(junit_path)],
        'jacoco_status': 'not-applicable',
        'jacoco_summary': '',
        'jacoco_report_xml': '',
        'jacoco_report_html': '',
        'jacoco_counters': {},
        'jacoco_targets': [],
        'jacoco_bundle_name': '',
    }

    try:
        if not selector:
            raise RuntimeError('TEST_CLASS_SELECTOR is required. Resolve the Jira mapping first.')

        command = ['npx', 'playwright', 'test', '--grep', selector]
        exit_code = run_command(command, cwd=root_dir)
        result['test_exit_code'] = exit_code

        stats = parse_junit(junit_path)
        result.update(stats)
        result['jacoco_report_html'] = str(html_dir / 'index.html')

        if int(stats['tests']) > 0 and (int(stats['failures']) > 0 or int(stats['errors']) > 0):
            result['status'] = 'failure'
            result['category'] = 'test-assertion-failed'
            result['failure_summary'] = str(stats['failure_summary'] or 'Playwright assertions failed.')
        elif exit_code == 0:
            result['status'] = 'success'
            result['category'] = 'success'
            result['failure_summary'] = ''
        else:
            result['status'] = 'failure'
            result['category'] = 'test-infrastructure-failed'
            result['failure_summary'] = 'Playwright failed before producing assertion results.'
    except Exception as exc:
        result['status'] = 'failure'
        result['category'] = 'test-infrastructure-failed'
        result['failure_summary'] = f'{exc.__class__.__name__}: {exc}'
        result['stacktrace'] = traceback.format_exc()
    finally:
        write_text(artifact_dir / 'run-metadata.txt', '\n'.join([
            f"Selected test: {selector}",
            'Execution method: playwright',
            f"Result category: {result['category']}",
            f"Failure summary: {result['failure_summary']}",
            f"JUnit report: {junit_path}",
            f"HTML report: {html_dir}",
        ]))
        write_text(artifact_dir / 'run-summary.txt', '\n'.join([
            '### Test run result',
            f"- Result category: {result['category']}",
            f"- Failure summary: {result['failure_summary'] or 'none'}",
            f"- Selected test: {selector or 'none'}",
            f"- Execution method: playwright",
            f"- Totals: tests={result['tests']} failures={result['failures']} errors={result['errors']} skipped={result['skipped']}",
            '',
        ]))
        write_json(artifact_dir / 'run-result.json', result)

    return 0 if result['category'] == 'success' else 1


if __name__ == '__main__':
    raise SystemExit(main())
