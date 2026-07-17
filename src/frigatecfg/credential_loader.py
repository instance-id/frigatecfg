"""Load credentials from environment variables on startup.

Env var pattern:
    CREDENTIAL_USERNAME_<NAME>="user"
    CREDENTIAL_PASSWORD_<NAME>="pass"

Pairs are matched by <NAME> suffix. Underscores in <NAME> are converted
to hyphens for the stored credential name (e.g. REOLINK_1 → reolink-1).

Env-sourced credentials are marked source='env' and are read-only in UI.
"""

from __future__ import annotations

import os
import re

from . import models


def load_env_credentials() -> int:
    """Scan os.environ for CREDENTIAL_USERNAME_* / CREDENTIAL_PASSWORD_* pairs.

    Upserts matching pairs into the credentials table with source='env'.
    Returns count of credentials loaded.
    """
    username_prefix = "CREDENTIAL_USERNAME_"
    password_prefix = "CREDENTIAL_PASSWORD_"

    usernames: dict[str, str] = {}
    passwords: dict[str, str] = {}

    for key, value in os.environ.items():
        if key.startswith(username_prefix):
            raw_name = key[len(username_prefix):]
            usernames[raw_name] = value
        elif key.startswith(password_prefix):
            raw_name = key[len(password_prefix):]
            passwords[raw_name] = value

    count = 0
    for raw_name, username in usernames.items():
        password = passwords.get(raw_name)
        if password is None:
            continue
        # Convert underscores to hyphens, lowercase for friendly display
        display_name = raw_name.replace("_", "-").lower()
        models.upsert_credential(display_name, username, password, source="env")
        count += 1

    return count
