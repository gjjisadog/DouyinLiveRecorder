from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path


def classify_check_failure(message: str) -> str:
    text = message.lower()
    if any(marker in text for marker in ("captcha", "risk", "verify", "412", "429")):
        return "risk_control"
    if any(marker in text for marker in ("401", "403", "cookie", "login required")):
        return "cookie_invalid"
    if any(
        marker in text
        for marker in (
            "timed out",
            "timeout",
            "connection reset",
            "connection refused",
            "network is unreachable",
            "name resolution",
        )
    ):
        return "network"
    return "resolver_error"


def sanitize_sample(message: str) -> str:
    value = re.sub(r"https?://\S+", "<url>", message)
    value = re.sub(
        r"(?i)\b(cookie|authorization|token|password)\b[\"']?\s*[:=]\s*[\"']?[^,;\s}\]]+",
        r"\1=<redacted>",
        value,
    )
    return " ".join(value.split())[:500]


class ObservationStore:
    """Keep bounded, secret-safe resolver failure evidence for long-run checks."""

    def __init__(self, state_path: Path, *, max_samples: int = 50) -> None:
        self.path = state_path / "error_observations.json"
        self.max_samples = max_samples
        self._lock = threading.Lock()
        self._payload = self._load()

    def _load(self) -> dict:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {}
        counters = payload.get("counters")
        samples = payload.get("samples")
        safe_counters: dict[str, int] = {}
        if isinstance(counters, dict):
            for key, value in counters.items():
                try:
                    safe_counters[str(key)] = max(0, int(value))
                except (TypeError, ValueError):
                    continue
        return {
            "counters": safe_counters,
            "samples": samples if isinstance(samples, list) else [],
        }

    def record(self, category: str, error: BaseException) -> str:
        safe_message = sanitize_sample(str(error))
        fingerprint = hashlib.sha256(
            f"{type(error).__name__}:{safe_message}".encode("utf-8")
        ).hexdigest()[:16]
        with self._lock:
            counters = self._payload["counters"]
            counters[category] = int(counters.get(category, 0)) + 1
            self._payload["samples"].append(
                {
                    "timestamp": time.time(),
                    "category": category,
                    "error_type": type(error).__name__,
                    "fingerprint": fingerprint,
                    "message": safe_message,
                }
            )
            self._payload["samples"] = self._payload["samples"][-self.max_samples :]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self._payload, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(temporary, self.path)
        return fingerprint

    @property
    def counters(self) -> dict[str, int]:
        with self._lock:
            return dict(self._payload["counters"])
