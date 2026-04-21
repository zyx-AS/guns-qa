#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GUNS_REPO_URL="${GUNS_REPO_URL:-https://gitee.com/stylefeng/guns.git}"
GUNS_FALLBACK_REPO_URL="${GUNS_FALLBACK_REPO_URL:-https://gitcode.com/javaguns/guns.git}"
GUNS_DEFAULT_BRANCH="${GUNS_DEFAULT_BRANCH:-master}"
GUNS_REF="${GUNS_REF:-84272f5a324e0d7890d241d7ae9afa7398da49fa}"
GUNS_TEST_CLASS="${GUNS_TEST_CLASS:-cn.stylefeng.guns.core.security.BlackWhiteInterceptorTest}"
GUNS_WORK_DIR="${GUNS_WORK_DIR:-$ROOT_DIR/.tmp/guns-src}"
GUNS_ARTIFACT_DIR="${GUNS_ARTIFACT_DIR:-$ROOT_DIR/.artifacts/guns}"
LOCAL_M2_CACHE="${LOCAL_M2_CACHE:-$ROOT_DIR/.tmp/m2/repository}"
MAVEN_VERSION="${MAVEN_VERSION:-3.9.9}"
MAVEN_HOME_DIR="${MAVEN_HOME_DIR:-$ROOT_DIR/.tmp/tools/apache-maven-$MAVEN_VERSION}"

mkdir -p "$(dirname "$GUNS_WORK_DIR")" "$GUNS_ARTIFACT_DIR"
rm -rf "$GUNS_WORK_DIR"

clone_repo() {
  local repo_url
  for repo_url in "$GUNS_REPO_URL" "$GUNS_FALLBACK_REPO_URL"; do
    if [[ -z "$repo_url" ]]; then
      continue
    fi

    echo "Cloning GUNS from $repo_url"
    if git clone --depth 1 --branch "$GUNS_DEFAULT_BRANCH" "$repo_url" "$GUNS_WORK_DIR"; then
      return 0
    fi

    rm -rf "$GUNS_WORK_DIR"
    echo "Clone failed for $repo_url" >&2
  done

  echo "Unable to clone the GUNS repository." >&2
  exit 1
}

clone_repo

resolved_head="$(git -C "$GUNS_WORK_DIR" rev-parse HEAD)"
if [[ "$GUNS_REF" != "$resolved_head" ]]; then
  git -C "$GUNS_WORK_DIR" fetch --depth 1 origin "$GUNS_REF"
  git -C "$GUNS_WORK_DIR" checkout --detach FETCH_HEAD
  resolved_head="$(git -C "$GUNS_WORK_DIR" rev-parse HEAD)"
fi

if [[ -d "$ROOT_DIR/guns-tests" ]]; then
  echo "Copying test assets from guns-qa into the GUNS workspace"
  cp -R "$ROOT_DIR/guns-tests/." "$GUNS_WORK_DIR/"
fi

EXPECTED_TEST_PATH="$GUNS_WORK_DIR/src/test/java/cn/stylefeng/guns/core/security/BlackWhiteInterceptorTest.java"
if [[ ! -f "$EXPECTED_TEST_PATH" ]]; then
  echo "Expected test asset was not copied into the GUNS workspace: $EXPECTED_TEST_PATH" >&2
  exit 1
fi

echo "Running $GUNS_TEST_CLASS against $resolved_head"

run_with_maven() {
  mkdir -p "$LOCAL_M2_CACHE"
  (cd "$GUNS_WORK_DIR" && mvn -B -ntp "-Dmaven.repo.local=$LOCAL_M2_CACHE" "-Dtest=$GUNS_TEST_CLASS" test)
}

run_with_docker() {
  mkdir -p "$LOCAL_M2_CACHE"
  docker run --rm \
    -v "$GUNS_WORK_DIR:/workspace" \
    -v "$LOCAL_M2_CACHE:/root/.m2/repository" \
    -w /workspace \
    maven:3.9.9-eclipse-temurin-17 \
    mvn -B -ntp "-Dtest=$GUNS_TEST_CLASS" test
}

run_with_portable_maven() {
  local tools_dir archive_path archive_url
  tools_dir="$(dirname "$MAVEN_HOME_DIR")"
  archive_path="$tools_dir/apache-maven-$MAVEN_VERSION-bin.tar.gz"
  archive_url="https://archive.apache.org/dist/maven/maven-3/$MAVEN_VERSION/binaries/apache-maven-$MAVEN_VERSION-bin.tar.gz"

  mkdir -p "$tools_dir"
  if [[ ! -x "$MAVEN_HOME_DIR/bin/mvn" ]]; then
    echo "Downloading portable Maven $MAVEN_VERSION"
    if command -v curl >/dev/null 2>&1; then
      curl -fsSL "$archive_url" -o "$archive_path"
    elif command -v wget >/dev/null 2>&1; then
      wget -q -O "$archive_path" "$archive_url"
    else
      echo "Neither curl nor wget is available to download Maven." >&2
      exit 1
    fi
    tar -xzf "$archive_path" -C "$tools_dir"
  fi

  (cd "$GUNS_WORK_DIR" && "$MAVEN_HOME_DIR/bin/mvn" -B -ntp "-Dtest=$GUNS_TEST_CLASS" test)
}

if command -v mvn >/dev/null 2>&1; then
  run_with_maven
elif command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  run_with_docker
else
  run_with_portable_maven
fi

rm -rf "$GUNS_ARTIFACT_DIR/surefire-reports"
if [[ -d "$GUNS_WORK_DIR/target/surefire-reports" ]]; then
  mkdir -p "$GUNS_ARTIFACT_DIR"
  cp -R "$GUNS_WORK_DIR/target/surefire-reports" "$GUNS_ARTIFACT_DIR/"
fi

cat > "$GUNS_ARTIFACT_DIR/run-metadata.txt" <<EOF
GUNS repo: $GUNS_REPO_URL
Fallback repo: $GUNS_FALLBACK_REPO_URL
Pinned ref: $GUNS_REF
Resolved commit: $resolved_head
Selected test: $GUNS_TEST_CLASS
Workspace: $GUNS_WORK_DIR
Artifacts: $GUNS_ARTIFACT_DIR
EOF

echo "Run completed successfully."
