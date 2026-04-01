"""Desktop client entrypoint."""

from pathlib import Path
import sys

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from client.bootstrap import run


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
