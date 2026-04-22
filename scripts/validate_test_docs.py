from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CASE_ROOT = REPO_ROOT / "guns-tests" / "docs"
TEST_ROOT = REPO_ROOT / "guns-tests" / "src" / "test"
CASE_TYPES = {"unit", "integration", "system", "performance"}
REQUIRED_HEADINGS = [
    "## 1. 测试目的",
    "## 2. 测试方法与设计依据",
    "## 3. 前置条件",
    "## 4. 测试步骤",
    "## 5. 预期结果",
    "## 6. 实际结果",
    "## 7. 结论",
    "## 8. 测试过程中的差异情况",
]
TEST_FILE_PATTERNS = [
    "**/*Test.java",
    "**/*Test.kt",
    "**/*Test.js",
    "**/*Test.ts",
    "**/*Test.py",
]
CODE_REF_PATTERN = re.compile(r"^\|\s*对应代码\s*\|\s*`([^`]+)`\s*\|\s*$", re.MULTILINE)


def iter_case_readmes() -> list[Path]:
    readmes: list[Path] = []
    if not CASE_ROOT.exists():
        return readmes
    for path in CASE_ROOT.glob("*/*/README.md"):
        parts = path.relative_to(CASE_ROOT).parts
        if len(parts) == 3 and parts[0] in CASE_TYPES:
            readmes.append(path)
    return sorted(readmes)


def collect_test_files() -> list[Path]:
    files: set[Path] = set()
    if not TEST_ROOT.exists():
        return []
    for pattern in TEST_FILE_PATTERNS:
        for path in TEST_ROOT.glob(pattern):
            if path.is_file():
                files.add(path.resolve())
    return sorted(files)


def main() -> int:
    errors: list[str] = []
    documented_files: set[Path] = set()
    case_readmes = iter_case_readmes()

    for readme in case_readmes:
        text = readme.read_text(encoding="utf-8")
        missing = [heading for heading in REQUIRED_HEADINGS if heading not in text]
        if missing:
            errors.append(
                f"{readme.relative_to(REPO_ROOT)} 缺少必需章节: {', '.join(missing)}"
            )

        match = CODE_REF_PATTERN.search(text)
        if not match:
            errors.append(f"{readme.relative_to(REPO_ROOT)} 缺少 `对应代码` 元数据行")
            continue

        code_ref = match.group(1).strip()
        code_path = (REPO_ROOT / code_ref).resolve()
        if not code_path.exists():
            errors.append(
                f"{readme.relative_to(REPO_ROOT)} 引用的代码路径不存在: {code_ref}"
            )
            continue

        documented_files.add(code_path)

    for test_file in collect_test_files():
        if test_file not in documented_files:
            errors.append(
                f"测试文件缺少对应 README: {test_file.relative_to(REPO_ROOT)}"
            )

    if errors:
        print("Test documentation validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Test documentation validation passed.")
    print(f"Validated {len(case_readmes)} case README(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
