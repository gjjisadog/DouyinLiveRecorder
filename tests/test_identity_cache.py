from __future__ import annotations

from pathlib import Path

from app.identity_cache import IdentityCache, resolved_identity
from app.models import RoomConfig


def test_resolved_identity_prefers_stable_user_then_room() -> None:
    assert resolved_identity({"id_str": "123", "owner": {"sec_uid": "user-a"}}, {}) == "user:user-a"
    assert resolved_identity({"owner": {"sec_uid": "user-a"}}, {}) == "user:user-a"
    assert resolved_identity({"id_str": "123"}, {}) == "room:123"
    assert resolved_identity({}, {}) == ""


def test_identity_cache_persists_and_deduplicates_aliases(tmp_path: Path) -> None:
    cache = IdentityCache(tmp_path)
    short = RoomConfig("https://v.douyin.com/abc/")
    live = RoomConfig("https://live.douyin.com/123")
    cache.remember(short.url, "room:999")
    cache.remember(live.url, "room:999")

    reloaded = IdentityCache(tmp_path)
    assert reloaded.get(short.url) == "room:999"
    assert reloaded.deduplicate((short, live)) == (short,)


def test_corrupt_identity_cache_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "room_identities.json").write_text("{bad", encoding="utf-8")
    cache = IdentityCache(tmp_path)
    room = RoomConfig("https://live.douyin.com/123")
    assert cache.get(room.url) == ""
    assert cache.deduplicate((room,)) == (room,)
