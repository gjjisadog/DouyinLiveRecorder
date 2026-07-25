"""Fail CI when tracked text files are not UTF-8 or contain obvious mojibake."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

TEXT_SUFFIXES = {
    ".bat",
    ".css",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".svg",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}
MOJIBAKE_PATTERNS = (
    re.compile(r"\?{3,}"),
    re.compile("\N{REPLACEMENT CHARACTER}"),
    re.compile("\u951f\u65a4\u62f7|\u93c2\u56e6\u6b22|\u95bf\u951b\u6e80"),
)
LOCAL_PATH_PATTERN = re.compile(r"(?i)\bE:[/\\]Project[/\\]")


def tracked_text_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        check=True,
    )
    paths = []
    for raw_path in result.stdout.split(b"\0"):
        if not raw_path:
            continue
        relative = Path(raw_path.decode("utf-8"))
        if relative.suffix.lower() in TEXT_SUFFIXES:
            paths.append(relative)
    return paths


def validate(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relative in tracked_text_files(repo_root):
        path = repo_root / relative
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            errors.append(f"{relative}: invalid UTF-8: {exc}")
            continue
        for pattern in MOJIBAKE_PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                errors.append(f"{relative}:{line}: obvious mojibake: {match.group(0)!r}")
                break
        match = LOCAL_PATH_PATTERN.search(text)
        if match:
            line = text.count("\n", 0, match.start()) + 1
            errors.append(f"{relative}:{line}: machine-local absolute path")
    return errors


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    errors = validate(repo_root)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"UTF-8 validation passed for {len(tracked_text_files(repo_root))} tracked text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
