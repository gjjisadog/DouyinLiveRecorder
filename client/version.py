"""Client product metadata."""

from __future__ import annotations

APP_NAME = "DouyinLiveRecorder Client"
PRODUCT_NAME = "DouyinLiveRecorder Client"
COMPANY_NAME = "DouyinLiveRecorder"
ORGANIZATION_NAME = "DouyinLiveRecorder"
APP_VERSION = "4.0.7"
APP_VERSION_TAG = f"v{APP_VERSION}"
FILE_VERSION = (4, 0, 7, 0)


def file_version_string() -> str:
    return ".".join(str(part) for part in FILE_VERSION)


def windows_file_version() -> str:
    return ",".join(str(part) for part in FILE_VERSION)
