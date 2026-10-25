"""Maintenance commands.

Usage (from `backend/`):
    python -m app.cli purge-boards

Run it periodically (e.g. daily cron) to permanently delete boards whose 30-day restore window ended.
"""

import argparse
import asyncio

from app.database import SessionLocal, engine
from app.services.boards import purge_expired_boards


async def _purge_boards() -> int:
    try:
        async with SessionLocal() as db:
            return await purge_expired_boards(db)
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    parser.add_argument("command", choices=["purge-boards"])
    args = parser.parse_args()

    if args.command == "purge-boards":
        purged = asyncio.run(_purge_boards())
        print(f"Purged {purged} expired board(s).")


if __name__ == "__main__":
    main()
