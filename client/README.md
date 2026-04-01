# Client Desktop App

This directory contains the PySide6 desktop client.

Planned layers:
- `ui/`: desktop interface and pages
- `viewmodels/`: UI-facing state and commands
- `core/`: business services and domain models
- `platforms/`: platform adapters
- `infra/`: infrastructure concerns
- `resources/`: icons, styles, and assets
- `tests/`: client-side tests

Current UI:
- `TasksPage`: task list, add/edit, start/stop, local persistence
- `SettingsPage`: local config editing and saving
- `HistoryPage`: recording history list and export
- `LogsPage`: runtime logs with level/source filtering and statistics

Run:
- `python client/main.py`

Build:
- `python -m pip install -r requirements.client-build.txt`
- `python -m client.build_release --python <python.exe> --repo-root <repo-root>`
- Windows wrappers: `build_client_release.ps1` / `build_client_release.bat`
