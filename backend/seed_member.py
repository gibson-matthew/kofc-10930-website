"""Ensure the local test accounts exist in PostgreSQL.

Run from the repository root:

    .\\.venv\\Scripts\\python.exe backend\\seed_member.py

Creates membership id 1000000 (David Hernandez, GK, admin, webmaster) with password
Password123! when that member is not already stored. The same password is
used for 1000001 and for roster ids 1000100-1000149. Starting the API runs
the same step, including the 20-each past-honor lists.
"""

from __future__ import annotations

import sys

from db import store


def main() -> None:
    status = store.prepare()
    if status == "memory":
        print(
            "Could not reach PostgreSQL, so the test roster was not saved. "
            "Create the database, then run this script again.",
            file=sys.stderr,
        )
        sys.exit(1)
    if status == "different-password":
        print(
            "Member 1000000 already exists with a different password. "
            "The stored password was left unchanged. "
            "Roster 1000100-1000149 still uses password Password123!.",
            file=sys.stderr,
        )
        sys.exit(2)
    print(f"Test member 1000000 is ready ({status}).")
    print("Roster 1000100-1000149 uses password Password123!.")


if __name__ == "__main__":
    main()
