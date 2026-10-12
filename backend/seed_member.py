"""Ensure the local test member exists in PostgreSQL.

Run from the repository root:

    .\\.venv\\Scripts\\python.exe backend\\seed_member.py

Creates membership id 1000000 with password Password123! when that member
is not already stored. Starting the API runs the same step.
"""

from __future__ import annotations

import sys

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

from db import store


def main() -> None:
    status = store.prepare()
    if status == "memory":
        print(
            "Could not reach PostgreSQL, so the test member was not saved. "
            "Create the database, then run this script again.",
            file=sys.stderr,
        )
        sys.exit(1)
    if status == "different-password":
        print(
            "Member 1000000 already exists with a different password. "
            "The stored password was left unchanged.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(f"Test member 1000000 is ready ({status}).")


if __name__ == "__main__":
    main()
