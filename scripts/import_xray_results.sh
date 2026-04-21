#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XRAY_BASE_URL="${XRAY_BASE_URL:-https://us.xray.cloud.getxray.app}"
XRAY_PROJECT_KEY="${XRAY_PROJECT_KEY:-GUNSQA}"
XRAY_CLIENT_ID="${XRAY_CLIENT_ID:-}"
XRAY_CLIENT_SECRET="${XRAY_CLIENT_SECRET:-}"
XRAY_JIRA_ISSUE_KEY="${XRAY_JIRA_ISSUE_KEY:-}"
XRAY_REPORT_DIR="${XRAY_REPORT_DIR:-$ROOT_DIR/.artifacts/guns/surefire-reports}"
XRAY_ARTIFACT_DIR="${XRAY_ARTIFACT_DIR:-$ROOT_DIR/.artifacts/guns}"
RUN_METADATA_PATH="${RUN_METADATA_PATH:-$ROOT_DIR/.artifacts/guns/run-metadata.txt}"
GUNS_TEST_CLASS="${GUNS_TEST_CLASS:-unknown-test-class}"
GUNS_REF="${GUNS_REF:-unknown-guns-ref}"
GITHUB_RUN_ID="${GITHUB_RUN_ID:-local-run}"
GITHUB_RUN_NUMBER="${GITHUB_RUN_NUMBER:-local}"
GITHUB_SERVER_URL="${GITHUB_SERVER_URL:-https://github.com}"
GITHUB_REPOSITORY="${GITHUB_REPOSITORY:-zyx-AS/guns-qa}"
GITHUB_SHA="${GITHUB_SHA:-local-sha}"
GITHUB_HEAD_REF="${GITHUB_HEAD_REF:-}"
GITHUB_REF_NAME="${GITHUB_REF_NAME:-}"

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
  for candidate in \
    "$XRAY_JIRA_ISSUE_KEY" \
    "$GITHUB_HEAD_REF" \
    "$GITHUB_REF_NAME"; do
    if [[ "$candidate" =~ ([A-Z][A-Z0-9]+-[0-9]+) ]]; then
      echo "${BASH_REMATCH[1]}"
      return 0
    fi
  done
  return 1
}

ISSUE_KEY="$(detect_issue_key || true)"
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

to_curl_path() {
  local input_path="$1"
  if command -v cygpath >/dev/null 2>&1; then
    cygpath -w "$input_path"
  else
    printf '%s\n' "$input_path"
  fi
}

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

cat > "$INFO_PATH" <<EOF
{"fields":{"project":{"key":"$XRAY_PROJECT_KEY"},"summary":"$SUMMARY_TEXT","issuetype":{"name":"Test Execution"},"labels":["guns-qa","github-actions","xray-auto-import"]}}
EOF

cat > "$TEST_INFO_PATH" <<EOF
{"fields":{"project":{"key":"$XRAY_PROJECT_KEY"},"issuetype":{"name":"Test"},"labels":["guns-qa","automation","$SAFE_TEST_LABEL"]}}
EOF

AUTH_PAYLOAD="{\"client_id\":\"$XRAY_CLIENT_ID\",\"client_secret\":\"$XRAY_CLIENT_SECRET\"}"
AUTH_TOKEN="$(curl -fsS -X POST "$XRAY_BASE_URL/api/v2/authenticate" -H 'Content-Type: application/json' --data "$AUTH_PAYLOAD")"
AUTH_TOKEN="${AUTH_TOKEN%\"}"
AUTH_TOKEN="${AUTH_TOKEN#\"}"

RESULTS_UPLOAD_PATH="$(to_curl_path "$MERGED_REPORT_PATH")"
INFO_UPLOAD_PATH="$(to_curl_path "$INFO_PATH")"
TEST_INFO_UPLOAD_PATH="$(to_curl_path "$TEST_INFO_PATH")"

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

XRAY_EXECUTION_URL=""
if [[ -n "$XRAY_EXECUTION_KEY" ]]; then
  XRAY_EXECUTION_URL="https://jira20260410.atlassian.net/browse/$XRAY_EXECUTION_KEY"
fi

cat > "$XRAY_SUMMARY_PATH" <<EOF
Xray project: $XRAY_PROJECT_KEY
Source issue key: ${ISSUE_KEY:-none}
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
  } >> "$GITHUB_OUTPUT"
fi

echo "Imported JUnit results to Xray: ${XRAY_EXECUTION_KEY:-unknown}"
