from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Iterable

from .models import RoomConfig


class IdentityCache:
    """Persist resolved room identities so URL aliases need only one future check."""

    def __init__(self, state_path: Path) -> None:
        self.path = state_path / "room_identities.json"
        self._lock = threading.RLock()
        self._identities = self._load()

    def _load(self) -> dict[str, str]:
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        if not isinstance(payload, dict):
            return {}
        return {
            str(url): str(identity)
            for url, identity in payload.items()
            if isinstance(url, str) and isinstance(identity, str) and identity
        }

    def get(self, url: str) -> str:
        with self._lock:
            return self._identities.get(url, "")

    def remember(self, url: str, identity: str) -> None:
        if not identity:
            return
        with self._lock:
            if self._identities.get(url) == identity:
                return
            self._identities[url] = identity
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(self._identities, ensure_ascii=False, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(temporary, self.path)

    def deduplicate(self, rooms: Iterable[RoomConfig]) -> tuple[RoomConfig, ...]:
        unique: list[RoomConfig] = []
        seen: set[str] = set()
        with self._lock:
            for room in rooms:
                identity = self._identities.get(room.url)
                key = f"identity:{identity}" if identity else f"url:{room.url}"
                if key in seen:
                    continue
                seen.add(key)
                unique.append(room)
        return tuple(unique)


def resolved_identity(data: dict, result: dict) -> str:
    owner = data.get("owner") if isinstance(data.get("owner"), dict) else {}
    sec_uid = data.get("sec_uid") or owner.get("sec_uid") or owner.get("sec_user_id")
    if sec_uid:
        return f"user:{sec_uid}"
    room_id = (
        data.get("id_str")
        or data.get("id")
        or data.get("room_id")
        or result.get("room_id")
        or result.get("web_rid")
    )
    if room_id:
        return f"room:{room_id}"
    return ""
