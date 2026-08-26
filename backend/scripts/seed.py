#!/usr/bin/env python3
"""Seed script that runs super admin seeding."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.seed import seed_super_admin  # noqa: E402


async def main():
    try:
        await seed_super_admin()
    except Exception as e:
        print(f"Seed error (may be ok if already seeded): {e}")


if __name__ == "__main__":
    asyncio.run(main())
