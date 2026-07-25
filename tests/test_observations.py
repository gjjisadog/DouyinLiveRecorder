from __future__ import annotations

import json
from pathlib import Path

from app.observations import ObservationStore, classify_check_failure, sanitize_sample


def test_classifies_cookie_risk_and_network_failures() -> None:
    assert classify_check_failure("HTTP 403 forbidden") == "cookie_invalid"
    assert classify_check_failure("HTTP 403 captcha verification") == "risk_control"
    assert classify_check_failure("captcha verification required") == "risk_control"
    assert classify_check_failure("connection timed out") == "network"
    assert classify_check_failure("unexpected payload") == "resolver_error"


def test_observation_store_redacts_and_bounds_samples(tmp_path: Path) -> None:
    store = ObservationStore(tmp_path, max_samples=2)
    store.record("cookie_invalid", RuntimeError("cookie=secret https://example.test/a?token=x"))
    store.record("risk_control", ValueError("captcha"))
    store.record("network", TimeoutError("timeout"))

    payload = json.loads((tmp_path / "error_observations.json").read_text(encoding="utf-8"))
    assert payload["counters"] == {
        "cookie_invalid": 1,
        "network": 1,
        "risk_control": 1,
    }
    assert len(payload["samples"]) == 2
    serialized = json.dumps(payload)
    assert "secret" not in serialized
    assert "example.test" not in serialized


def test_sanitize_sample_removes_urls_and_secret_values() -> None:
    safe = sanitize_sample("authorization: bearer-secret https://example.test/live?id=secret")
    assert safe == "authorization=<redacted> <url>"
    assert sanitize_sample("{'cookie': 'raw-secret'}") == "{'cookie=<redacted>}"
