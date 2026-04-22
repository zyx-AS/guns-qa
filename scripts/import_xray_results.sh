#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XRAY_BASE_URL="${XRAY_BASE_URL:-https://us.xray.cloud.getxray.app}"
XRAY_PROJECT_KEY="${XRAY_PROJECT_KEY:-GUNSQA}"
XRAY_CLIENT_ID="${XRAY_CLIENT_ID:-}"
XRAY_CLIENT_SECRET="${XRAY_CLIENT_SECRET:-}"
XRAY_JIRA_ISSUE_KEY="${XRAY_JIRA_ISSUE_KEY:-}"
XRAY_TEST_EXECUTION_KEY="${XRAY_TEST_EXECUTION_KEY:-}"
XRAY_TEST_EXECUTION_MAP_PATH="${XRAY_TEST_EXECUTION_MAP_PATH:-$ROOT_DIR/config/xray-test-executions.json}"
XRAY_REPORT_DIR="${XRAY_REPORT_DIR:-$ROOT_DIR/.artifacts/guns/surefire-reports}"
XRAY_ARTIFACT_DIR="${XRAY_ARTIFACT_DIR:-$ROOT_DIR/.artifacts/guns}"
RUN_METADATA_PATH="${RUN_METADATA_PATH:-$ROOT_DIR/.artifacts/guns/run-metadata.txt}"
JIRA_BASE_URL="${JIRA_BASE_URL:-https://jira20260410.atlassian.net}"
GUNS_TEST_CLASS="${GUNS_TEST_CLASS:-unknown-test-class}"
GUNS_REF="${GUNS_REF:-unknown-guns-ref}"
GITHUB_RUN_ID="${GITHUB_RUN_ID:-local-run}"
GITHUB_RUN_NUMBER="${GITHUB_RUN_NUMBER:-local}"
GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-zyx-AS/guns-qa}"
GITHUB_SHA="${GITHUB_SHA:-local-sha}"
GITHUB_HEAD_REF="${GITHUB_HEAD_REF:-}"
GITHUB_REF_NAME="${GITHUB_REF_NAME:-}"
GITHUB_EVENT_PATH="${GITHUB_EVENT_PATH:-}"

mkdir -p "$XRAY_ARTIFACT_DIR"

if [[ -z "$XRAY_CLIENT_ID" || -z "$XRAY_CLIENT_SECRET" ]]; then
  echo "XRAY_CLIENT_ID and XRAY_CLIENT_SECRET are required." >&2
  exit 1
fi

if [[ ! -d "$XRAY_REPORT_DIR" ]]; then
  echo "JUnit report directory does not exist: $XRAY_REPORT_DIR" >&2
  exit 1
fi

metadata_value() {
  local key="$1"
  if [[ -f "$RUN_METADATA_PATH" ]]; then
    sed -n "s/^$key: //p" "$RUN_METADATA_PATH" | head -n 1
  fi
}

if [[ "$GUNS_TEST_CLASS" == "unknown-test-class" ]]; then
  GUNS_TEST_CLASS="$(metadata_value 'Selected test' || true)"
  GUNS_TEST_CLASS="${GUNS_TEST_CLASS:-unknown-test-class}"
fi

if [[ "$GUNS_REF" == "unknown-guns-ref" ]]; then
  GUNS_REF="$(metadata_value 'Pinned ref' || true)"
  GUNS_REF="${GUNS_REF:-unknown-guns-ref}"
fi

detect_issue_key() {
  local candidate
  local event_key=""
  for candidate in \
    "$XRAY_JIRA_ISSUE_KEY" \
    "$GITHUB_HEAD_REF" \
    "$GITHUB_REF_NAME"; do
    if [[ "$candidate" =~ ([A-Z][A-Z0-9]+-[0-9]+) ]]; then
      echo "${BASH_REMATCH[1]}"
      return 0
    fi
  done
  if [[ -n "$GITHUB_EVENT_PATH" && -f "$GITHUB_EVENT_PATH" ]]; then
    event_key="$(python3 - "$GITHUB_EVENT_PATH" <<'PY' || true
import json
import re
import sys

pattern = re.compile(r'([A-Z][A-Z0-9]+-\d+)')

def emit_match(value):
    if not value:
        return False
    match = pattern.search(str(value))
    if match:
        print(match.group(1))
        return True
    return False

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    payload = json.load(fh)

for candidate in (
    payload.get("head_commit", {}).get("message"),
    payload.get("pull_request", {}).get("title"),
    payload.get("pull_request", {}).get("head", {}).get("ref"),
):
    if emit_match(candidate):
        raise SystemExit(0)

for commit in payload.get("commits", []):
    if emit_match(commit.get("message")):
        raise SystemExit(0)

raise SystemExit(1)
PY
)"
    if [[ -n "$event_key" ]]; then
      echo "$event_key"
      return 0
    fi
  fi
  return 1
}

lookup_test_execution_key_from_map() {
  local issue_key="$1"
  if [[ -z "$issue_key" || ! -f "$XRAY_TEST_EXECUTION_MAP_PATH" ]]; then
    return 1
  fi

  python3 - "$XRAY_TEST_EXECUTION_MAP_PATH" "$issue_key" <<'PY'
import json
import sys

map_path = sys.argv[1]
issue_key = sys.argv[2]

with open(map_path, "r", encoding="utf-8") as fh:
    data = json.load(fh)

value = data.get(issue_key)
if isinstance(value, str) and value.strip():
    print(value.strip())
elif isinstance(value, dict):
    for candidate in ("testExecutionKey", "executionKey", "xrayTestExecutionKey"):
        mapped = value.get(candidate)
        if isinstance(mapped, str) and mapped.strip():
            print(mapped.strip())
            break
PY
}

to_curl_path() {
  local input_path="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$input_path"
  else
    printf '%s\n' "$input_path"
  fi
}

ISSUE_KEY="$(detect_issue_key || true)"
EXECUTION_KEY_SOURCE="workflow-input"
if [[ -z "$XRAY_TEST_EXECUTION_KEY" ]]; then
  XRAY_TEST_EXECUTION_KEY="$(lookup_test_execution_key_from_map "$ISSUE_KEY" || true)"
  EXECUTION_KEY_SOURCE="mapping-file"
fi
if [[ -z "$XRAY_TEST_EXECUTION_KEY" ]]; then
  EXECUTION_KEY_SOURCE="created-new"
fi

if [[ -z "$ISSUE_KEY" && -z "$XRAY_TEST_EXECUTION_KEY" ]]; then
  cat > "$XRAY_ARTIFACT_DIR/xray-import-summary.txt" <<EOF
Xray project: $XRAY_PROJECT_KEY
Import mode: skipped-no-jira-context
Source issue key: none
Execution key source: none
Execution map path: ${XRAY_TEST_EXECUTION_MAP_PATH:-none}
Reason: no Jira issue key or explicit Xray Test Execution key was provided for this run
Selected test: $GUNS_TEST_CLASS
Pinned GUNS ref: $GUNS_REF
GitHub run: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID
GitHub commit: $GITHUB_SHA
EOF

  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    {
      echo "xray_execution_key="
      echo "xray_execution_url="
      echo "jira_issue_key="
      echo "xray_import_mode=skipped-no-jira-context"
    } >> "$GITHUB_OUTPUT"
  fi

  echo "Skipping Xray import because no Jira issue key or explicit execution key was provided."
  exit 0
fi

SUMMARY_PREFIX="GUNS unit test CI"
if [[ -n "$ISSUE_KEY" ]]; then
  SUMMARY_PREFIX="[$ISSUE_KEY] $SUMMARY_PREFIX"
fi

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT

MERGED_REPORT_PATH="$WORK_DIR/junit-report.xml"
INFO_PATH="$WORK_DIR/info.json"
TEST_INFO_PATH="$WORK_DIR/testInfo.json"
XRAY_RESPONSE_PATH="$XRAY_ARTIFACT_DIR/xray-import-response.json"
XRAY_SUMMARY_PATH="$XRAY_ARTIFACT_DIR/xray-import-summary.txt"

python3 - "$XRAY_REPORT_DIR" "$MERGED_REPORT_PATH" <<'PY'
import glob
import os
import shutil
import sys
import xml.etree.ElementTree as ET

report_dir = sys.argv[1]
output_path = sys.argv[2]
files = sorted(glob.glob(os.path.join(report_dir, "TEST-*.xml")))
if not files:
    raise SystemExit(f"No JUnit XML files found in {report_dir}")
if len(files) == 1:
    shutil.copyfile(files[0], output_path)
    raise SystemExit(0)
root = ET.Element("testsuites")
for path in files:
    tree = ET.parse(path)
    root.append(tree.getroot())
ET.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
PY

SUMMARY_TEXT="$SUMMARY_PREFIX / $GUNS_TEST_CLASS / run $GITHUB_RUN_NUMBER"
SAFE_TEST_LABEL="$(echo "$GUNS_TEST_CLASS" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-')"
SAFE_TEST_LABEL="${SAFE_TEST_LABEL#-}"
SAFE_TEST_LABEL="${SAFE_TEST_LABEL%-}"
SAFE_ISSUE_LABEL=""
if [[ -n "$ISSUE_KEY" ]]; then
  SAFE_ISSUE_LABEL="$(echo "$ISSUE_KEY" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-')"
  SAFE_ISSUE_LABEL="${SAFE_ISSUE_LABEL#-}"
  SAFE_ISSUE_LABEL="${SAFE_ISSUE_LABEL%-}"
fi

python3 - "$INFO_PATH" "$TEST_INFO_PATH" "$XRAY_PROJECT_KEY" "$SUMMARY_TEXT" "$SAFE_TEST_LABEL" "$SAFE_ISSUE_LABEL" "$ISSUE_KEY" "$GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID" "$GITHUB_SHA" <<'PY'
import json
import sys

info_path = sys.argv[1]
test_info_path = sys.argv[2]
project_key = sys.argv[3]
summary = sys.argv[4]
safe_test_label = sys.argv[5]
safe_issue_label = sys.argv[6]
issue_key = sys.argv[7]
run_url = sys.argv[8]
github_sha = sys.argv[9]

info_labels = ["guns-qa", "github-actions", "xray-auto-import"]
if safe_issue_label:
    info_labels.append(f"source-{safe_issue_label}")

info_payload = {
    "fields": {
        "project": {"key": project_key},
        "summary": summary,
        "description": "\n".join(
            [
                f"Source Jira issue: {issue_key or 'none'}",
                f"GitHub run: {run_url}",
                f"GitHub commit: {github_sha}",
            ]
        ),
        "issuetype": {"name": "Test Execution"},
        "labels": info_labels,
    }
}

test_payload = {
    "fields": {
        "project": {"key": project_key},
        "issuetype": {"name": "Test"},
        "labels": ["guns-qa", "automation", safe_test_label or "guns-unit-test"],
    }
}

with open(info_path, "w", encoding="utf-8") as fh:
    json.dump(info_payload, fh, ensure_ascii=False)

with open(test_info_path, "w", encoding="utf-8") as fh:
    json.dump(test_payload, fh, ensure_ascii=False)
PY

AUTH_PAYLOAD="{\"client_id\":\"$XRAY_CLIENT_ID\",\"client_secret\":\"$XRAY_CLIENT_SECRET\"}"
AUTH_TOKEN="$(curl -fsS -X POST "$XRAY_BASE_URL/api/v2/authenticate" -H 'Content-Type: application/json' --data "$AUTH_PAYLOAD")"
AUTH_TOKEN="${AUTH_TOKEN%\"}"
AUTH_TOKEN="${AUTH_TOKEN#\"}"

RESULTS_UPLOAD_PATH="$(to_curl_path "$MERGED_REPORT_PATH")"
INFO_UPLOAD_PATH="$(to_curl_path "$INFO_PATH")"
TEST_INFO_UPLOAD_PATH="$(to_curl_path "$TEST_INFO_PATH")"

XRAY_IMPORT_MODE="create-new-execution"
XRAY_EXECUTION_KEY=""
if [[ -n "$XRAY_TEST_EXECUTION_KEY" ]]; then
  XRAY_IMPORT_MODE="reuse-existing-execution"
  XRAY_EXECUTION_KEY="$XRAY_TEST_EXECUTION_KEY"
  curl -fsS -X POST "$XRAY_BASE_URL/api/v2/import/execution/junit?projectKey=$XRAY_PROJECT_KEY&testExecKey=$XRAY_TEST_EXECUTION_KEY" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -H "Content-Type: text/xml" \
    --data-binary "@$RESULTS_UPLOAD_PATH" \
    > "$XRAY_RESPONSE_PATH"
else
  curl -fsS -X POST "$XRAY_BASE_URL/api/v2/import/execution/junit/multipart" \
    -H "Authorization: Bearer $AUTH_TOKEN" \
    -F "results=@$RESULTS_UPLOAD_PATH;type=text/xml" \
    -F "info=@$INFO_UPLOAD_PATH;type=application/json" \
    -F "testInfo=@$TEST_INFO_UPLOAD_PATH;type=application/json" \
    > "$XRAY_RESPONSE_PATH"

  XRAY_EXECUTION_KEY="$(python3 - "$XRAY_RESPONSE_PATH" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    data = json.load(fh)

print(data.get("key", ""))
PY
)"
fi

XRAY_EXECUTION_URL=""
if [[ -n "$XRAY_EXECUTION_KEY" ]]; then
  XRAY_EXECUTION_URL="$JIRA_BASE_URL/browse/$XRAY_EXECUTION_KEY"
fi

cat > "$XRAY_SUMMARY_PATH" <<EOF
Xray project: $XRAY_PROJECT_KEY
Import mode: $XRAY_IMPORT_MODE
Source issue key: ${ISSUE_KEY:-none}
Execution key source: $EXECUTION_KEY_SOURCE
Execution map path: ${XRAY_TEST_EXECUTION_MAP_PATH:-none}
Execution issue key: ${XRAY_EXECUTION_KEY:-unknown}
Execution issue url: ${XRAY_EXECUTION_URL:-unknown}
Selected test: $GUNS_TEST_CLASS
Pinned GUNS ref: $GUNS_REF
GitHub run: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID
GitHub commit: $GITHUB_SHA
EOF

if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
  {
    echo "xray_execution_key=$XRAY_EXECUTION_KEY"
    echo "xray_execution_url=$XRAY_EXECUTION_URL"
    echo "jira_issue_key=$ISSUE_KEY"
    echo "xray_import_mode=$XRAY_IMPORT_MODE"
  } >> "$GITHUB_OUTPUT"
fi

echo "Imported JUnit results to Xray: ${XRAY_EXECUTION_KEY:-unknown}"
