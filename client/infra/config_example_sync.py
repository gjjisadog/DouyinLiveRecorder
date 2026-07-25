"""Validation helpers for public config example files."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ConfigSyncResult:
    ok: bool
    checked_files: list[Path]
    errors: list[str]


def load_ini_structure(path: Path) -> dict[str, set[str]]:
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read(path, encoding="utf-8-sig")
    return {section: set(parser[section].keys()) for section in parser.sections()}


def compare_ini_structure(source_path: Path, example_path: Path) -> list[str]:
    errors: list[str] = []
    source_sections = load_ini_structure(source_path)
    example_sections = load_ini_structure(example_path)

    missing_sections = sorted(set(source_sections) - set(example_sections))
    if missing_sections:
        errors.append(
            f"{example_path} 缺少 section: {', '.join(missing_sections)}"
        )

    for section in sorted(set(source_sections) & set(example_sections)):
        missing_keys = sorted(source_sections[section] - example_sections[section])
        if missing_keys:
            errors.append(
                f"{example_path} 在 section [{section}] 缺少 keys: {', '.join(missing_keys)}"
            )

    return errors


def validate_url_example(path: Path) -> list[str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    active_entries = [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]
    if active_entries:
        return []
    return [f"{path} 需要至少保留一条非注释示例地址，避免公开模板为空。"]


def validate_config_examples(repo_root: Path) -> ConfigSyncResult:
    config_ini = repo_root / "config" / "config.ini"
    config_example_ini = repo_root / "config" / "config.example.ini"
    url_example_ini = repo_root / "config" / "URL_config.example.ini"

    checked_files = [config_ini, config_example_ini, url_example_ini]
    errors: list[str] = []

    for path in checked_files:
        if not path.exists():
            errors.append(f"缺少文件: {path}")

    if errors:
        return ConfigSyncResult(ok=False, checked_files=checked_files, errors=errors)

    errors.extend(compare_ini_structure(config_ini, config_example_ini))
    errors.extend(validate_url_example(url_example_ini))
    return ConfigSyncResult(ok=not errors, checked_files=checked_files, errors=errors)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    result = validate_config_examples(repo_root)
    if result.ok:
        print("PASS: config example files are in sync.")
        for path in result.checked_files:
            print(f"- {path}")
        return 0

    print("FAIL: config example validation failed.")
    for error in result.errors:
        print(f"- {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
