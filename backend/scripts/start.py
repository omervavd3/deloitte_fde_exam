"""Container entrypoint: make sure the T-100 extract exists, then serve.

The download is a one-off (~18 MB, ~80s). data/raw is bind-mounted from the
host, so it survives rebuilds and only ever runs on a genuinely empty checkout.

Deliberately fail-soft: if TranStats is down or has changed its form, this logs
and starts the API anyway. The extract is additive - without it the frame keeps
exactly the columns it had before, so a failed download costs seven columns,
never a boot.

Env:
    SKIP_T100_DOWNLOAD=1   never fetch (CI, offline work)
    T100_YEAR=2026         year to request, defaults to the script's own default
"""

import os
import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from app.data.sources.t100_segment import find_extract  # noqa: E402

FETCH = BACKEND / "scripts" / "fetch_t100_segment.py"
TRUTHY = {"1", "true", "yes", "on"}


def ensure_extract() -> None:
    if os.getenv("SKIP_T100_DOWNLOAD", "").lower() in TRUTHY:
        print("[start] SKIP_T100_DOWNLOAD set - not fetching T-100 extract")
        return

    existing = find_extract()
    if existing is not None:
        print(f"[start] T-100 extract present: {existing.name}")
        return

    year = os.getenv("T100_YEAR")
    command = [sys.executable, str(FETCH)] + (["--year", year] if year else [])
    print("[start] no T-100 extract found - downloading once, this takes ~80s")
    try:
        result = subprocess.run(command, cwd=BACKEND, timeout=900)
        if result.returncode != 0:
            print(
                "[start] T-100 download failed; starting without it. "
                "The seven segment columns will be absent until a file is "
                "placed in data/raw/.",
                file=sys.stderr,
            )
    except Exception as exc:  # network, timeout, missing script
        print(f"[start] T-100 download error ({exc}); starting without it", file=sys.stderr)


def main() -> None:
    ensure_extract()
    argv = [
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        os.getenv("PORT", "8000"),
    ]
    if os.getenv("UVICORN_RELOAD", "1").lower() in TRUTHY:
        argv.append("--reload")
    print(f"[start] exec: {' '.join(argv)}")
    # exec rather than spawn so uvicorn owns PID 1 and docker stop reaches it.
    os.execvp(argv[0], argv)


if __name__ == "__main__":
    main()
