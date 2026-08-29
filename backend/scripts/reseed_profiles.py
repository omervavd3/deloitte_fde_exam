"""Push retuned built-in profile weights into an existing database.

`repository.seed_profiles` inserts ON CONFLICT DO NOTHING so a redeploy cannot
discard a profile someone edited in the dashboard, which means a deliberate
change to DEFAULT_PROFILES needs a deliberate push.

    python scripts/reseed_profiles.py            # show what would change
    python scripts/reseed_profiles.py --apply    # write it

Only rows with is_builtin = true are touched, so user-created profiles are never
affected. A built-in edited in the dashboard IS overwritten - that is the point
of the command, so the dry run lists it first.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from psycopg.rows import dict_row  # noqa: E402
from psycopg_pool import AsyncConnectionPool  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.scoring.profiles import DEFAULT_PROFILES  # noqa: E402


def _diff(current: dict, spec: dict) -> list[str]:
    """Human-readable weight changes, including metrics added or dropped."""
    changes = []
    for metric in sorted(set(current) | set(spec["weights"])):
        before, after = current.get(metric, 0.0), spec["weights"].get(metric, 0.0)
        if abs(before - after) > 1e-9:
            changes.append(f"{metric}: {before:.2f} -> {after:.2f}")
    return changes


async def run(apply: bool) -> int:
    settings = get_settings()
    async with AsyncConnectionPool(settings.database_url, open=False) as pool:
        await pool.open(wait=True)
        async with pool.connection() as conn:
            conn.row_factory = dict_row
            rows = await conn.execute(
                "SELECT name, weights, is_builtin FROM weight_profiles"
            )
            existing = {r["name"]: r for r in await rows.fetchall()}

            touched = 0
            for name, spec in DEFAULT_PROFILES.items():
                row = existing.get(name)
                if row is None:
                    print(f"+ {name}: new profile, will be inserted")
                    touched += 1
                elif not row["is_builtin"]:
                    print(f"  {name}: user-owned, left alone")
                    continue
                else:
                    changes = _diff(dict(row["weights"]), spec)
                    if not changes:
                        continue
                    print(f"~ {name}")
                    for line in changes:
                        print(f"    {line}")
                    touched += 1

                if apply:
                    await conn.execute(
                        """
                        INSERT INTO weight_profiles
                            (name, label, description, weights, is_builtin)
                        VALUES (%s, %s, %s, %s, true)
                        ON CONFLICT (name) DO UPDATE SET
                            label = EXCLUDED.label,
                            description = EXCLUDED.description,
                            weights = EXCLUDED.weights,
                            updated_at = now()
                        WHERE weight_profiles.is_builtin
                        """,
                        (name, spec["label"], spec["description"],
                         json.dumps(spec["weights"])),
                    )

            if not touched:
                print("nothing to do; built-in profiles already match the code")
            elif apply:
                print(f"\napplied to {touched} profile(s)")
            else:
                print(f"\n{touched} profile(s) would change; re-run with --apply")
    return 0


def _run(coro) -> int:
    """psycopg's async mode rejects the ProactorEventLoop Windows defaults to."""
    if sys.platform == "win32":
        loop = asyncio.SelectorEventLoop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    return asyncio.run(coro)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true",
                        help="write the changes instead of listing them")
    raise SystemExit(_run(run(parser.parse_args().apply)))
