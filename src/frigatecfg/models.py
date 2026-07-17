"""SQLite models for config versioning and metadata."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DB_PATH = Path(__file__).parent.parent.parent / "data" / "frigatecfg.db"


def get_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS config_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            config_yaml TEXT NOT NULL,
            config_json TEXT NOT NULL,
            description TEXT,
            created_at TEXT NOT NULL,
            is_current INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS undo_stack (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            section TEXT,
            entity_name TEXT,
            old_state TEXT,
            new_state TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS redo_stack (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            section TEXT,
            entity_name TEXT,
            old_state TEXT,
            new_state TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_config_versions_version ON config_versions(version);
        CREATE INDEX IF NOT EXISTS idx_undo_stack ON undo_stack(created_at);
        CREATE INDEX IF NOT EXISTS idx_redo_stack ON redo_stack(created_at);

        CREATE TABLE IF NOT EXISTS camera_metadata (
            camera_name TEXT PRIMARY KEY,
            notes TEXT,
            location TEXT,
            ip_address TEXT,
            manufacturer TEXT,
            model TEXT,
            purchase_date TEXT,
            firmware_version TEXT,
            serial_number TEXT,
            credential_id INTEGER,
            manual_username TEXT,
            manual_password TEXT,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS custom_brands (
            brand_key TEXT PRIMARY KEY,
            brand_data TEXT NOT NULL,
            is_override INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS scan_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            target TEXT UNIQUE NOT NULL,
            last_used TEXT NOT NULL,
            use_count INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS credentials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            username TEXT NOT NULL,
            password TEXT NOT NULL,
            source TEXT DEFAULT 'manual',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    # Migrations for existing DBs
    _migrate(conn)

    conn.close()


def _migrate(conn: sqlite3.Connection) -> None:
    """Run schema migrations for existing databases."""
    cols = [r[1] for r in conn.execute("PRAGMA table_info(camera_metadata)").fetchall()]
    if "serial_number" not in cols:
        conn.execute("ALTER TABLE camera_metadata ADD COLUMN serial_number TEXT")
    if "credential_id" not in cols:
        conn.execute("ALTER TABLE camera_metadata ADD COLUMN credential_id INTEGER")
    if "manual_username" not in cols:
        conn.execute("ALTER TABLE camera_metadata ADD COLUMN manual_username TEXT")
    if "manual_password" not in cols:
        conn.execute("ALTER TABLE camera_metadata ADD COLUMN manual_password TEXT")
    conn.commit()


def save_version(config_yaml: str, config_json: dict[str, Any], description: str = "") -> int:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    row = conn.execute("SELECT MAX(version) as max_ver FROM config_versions").fetchone()
    version = (row["max_ver"] or 0) + 1
    conn.execute("UPDATE config_versions SET is_current = 0")
    conn.execute(
        "INSERT INTO config_versions (version, config_yaml, config_json, description, created_at, is_current) VALUES (?, ?, ?, ?, ?, 1)",
        (version, config_yaml, json.dumps(config_json), description, now),
    )
    conn.commit()
    conn.close()
    return version


def get_current_version() -> dict[str, Any] | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM config_versions WHERE is_current = 1 ORDER BY version DESC LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def get_version(version: int) -> dict[str, Any] | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM config_versions WHERE version = ?", (version,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_versions(limit: int = 50) -> list[dict[str, Any]]:
    conn = get_db()
    rows = conn.execute(
        "SELECT id, version, description, created_at, is_current FROM config_versions ORDER BY version DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def push_undo(action: str, section: str | None, entity_name: str | None, old_state: Any, new_state: Any) -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO undo_stack (action, section, entity_name, old_state, new_state, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (action, section, entity_name, json.dumps(old_state), json.dumps(new_state), now),
    )
    conn.execute("DELETE FROM redo_stack")
    conn.commit()
    conn.close()


def pop_undo() -> dict[str, Any] | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM undo_stack ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        conn.execute("DELETE FROM undo_stack WHERE id = ?", (row["id"],))
        conn.execute(
            "INSERT INTO redo_stack (action, section, entity_name, old_state, new_state, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (row["action"], row["section"], row["entity_name"], row["old_state"], row["new_state"], row["created_at"]),
        )
        conn.commit()
        result = dict(row)
        result["old_state"] = json.loads(row["old_state"])
        result["new_state"] = json.loads(row["new_state"])
        conn.close()
        return result
    conn.close()
    return None


def pop_redo() -> dict[str, Any] | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM redo_stack ORDER BY id DESC LIMIT 1").fetchone()
    if row:
        conn.execute("DELETE FROM redo_stack WHERE id = ?", (row["id"],))
        conn.execute(
            "INSERT INTO undo_stack (action, section, entity_name, old_state, new_state, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (row["action"], row["section"], row["entity_name"], row["old_state"], row["new_state"], row["created_at"]),
        )
        conn.commit()
        result = dict(row)
        result["old_state"] = json.loads(row["old_state"])
        result["new_state"] = json.loads(row["new_state"])
        conn.close()
        return result
    conn.close()
    return None


def can_undo() -> bool:
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM undo_stack").fetchone()["c"]
    conn.close()
    return count > 0


def can_redo() -> bool:
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM redo_stack").fetchone()["c"]
    conn.close()
    return count > 0


def clear_stacks() -> None:
    conn = get_db()
    conn.execute("DELETE FROM undo_stack")
    conn.execute("DELETE FROM redo_stack")
    conn.commit()
    conn.close()


def get_camera_metadata(camera_name: str) -> dict[str, Any] | None:
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM camera_metadata WHERE camera_name = ?", (camera_name,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def set_camera_metadata(camera_name: str, data: dict[str, Any]) -> None:
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    fields = ["notes", "location", "ip_address", "manufacturer", "model", "purchase_date", "firmware_version", "serial_number"]
    values = {f: data.get(f, "") for f in fields}
    cred_id = data.get("credential_id")
    cred_val = int(cred_id) if cred_id else None
    manual_user = data.get("manual_username", "")
    manual_pass = data.get("manual_password", "")
    conn.execute(
        """INSERT INTO camera_metadata (camera_name, notes, location, ip_address, manufacturer, model, purchase_date, firmware_version, serial_number, credential_id, manual_username, manual_password, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(camera_name) DO UPDATE SET
             notes=excluded.notes, location=excluded.location, ip_address=excluded.ip_address,
             manufacturer=excluded.manufacturer, model=excluded.model,
             purchase_date=excluded.purchase_date, firmware_version=excluded.firmware_version,
             serial_number=excluded.serial_number, credential_id=excluded.credential_id,
             manual_username=excluded.manual_username, manual_password=excluded.manual_password,
             updated_at=excluded.updated_at""",
        (camera_name, values["notes"], values["location"], values["ip_address"],
         values["manufacturer"], values["model"], values["purchase_date"],
         values["firmware_version"], values["serial_number"], cred_val, manual_user, manual_pass, now),
    )
    conn.commit()
    conn.close()


def delete_camera_metadata(camera_name: str) -> None:
    conn = get_db()
    conn.execute("DELETE FROM camera_metadata WHERE camera_name = ?", (camera_name,))
    conn.commit()
    conn.close()


def rename_camera_metadata(old_name: str, new_name: str) -> None:
    conn = get_db()
    conn.execute("UPDATE camera_metadata SET camera_name = ? WHERE camera_name = ?", (new_name, old_name))
    conn.commit()
    conn.close()


# --- Custom brands ---

def get_all_custom_brands() -> list[dict[str, Any]]:
    """Get all custom brand entries from DB."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM custom_brands ORDER BY brand_key").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_custom_brand(brand_key: str) -> dict[str, Any] | None:
    """Get a single custom brand by key."""
    conn = get_db()
    row = conn.execute("SELECT * FROM custom_brands WHERE brand_key = ?", (brand_key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def save_custom_brand(brand_key: str, brand_data: dict[str, Any], is_override: bool = False) -> None:
    """Insert or update a custom brand entry."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO custom_brands (brand_key, brand_data, is_override, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(brand_key) DO UPDATE SET
             brand_data=excluded.brand_data, is_override=excluded.is_override,
             updated_at=excluded.updated_at""",
        (brand_key, json.dumps(brand_data), int(is_override), now, now),
    )
    conn.commit()
    conn.close()


def delete_custom_brand(brand_key: str) -> None:
    """Delete a custom brand entry."""
    conn = get_db()
    conn.execute("DELETE FROM custom_brands WHERE brand_key = ?", (brand_key,))
    conn.commit()
    conn.close()


# --- Scan target history ---

def save_scan_target(target: str) -> None:
    """Save or update a scan target in history."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO scan_targets (target, last_used, use_count)
           VALUES (?, ?, 1)
           ON CONFLICT(target) DO UPDATE SET
             last_used=excluded.last_used, use_count=scan_targets.use_count + 1""",
        (target, now),
    )
    conn.commit()
    conn.close()


def list_scan_targets() -> list[dict[str, Any]]:
    """List all scan targets ordered by most recently used."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM scan_targets ORDER BY last_used DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_scan_target(target: str) -> None:
    """Delete a scan target from history."""
    conn = get_db()
    conn.execute("DELETE FROM scan_targets WHERE target = ?", (target,))
    conn.commit()
    conn.close()


# --- Credentials ---

def list_credentials() -> list[dict[str, Any]]:
    """List all stored credentials, ordered by name."""
    conn = get_db()
    rows = conn.execute("SELECT * FROM credentials ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_credential(cred_id: int) -> dict[str, Any] | None:
    """Get a single credential by ID."""
    conn = get_db()
    row = conn.execute("SELECT * FROM credentials WHERE id = ?", (cred_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_credential_by_name(name: str) -> dict[str, Any] | None:
    """Get a single credential by name."""
    conn = get_db()
    row = conn.execute("SELECT * FROM credentials WHERE name = ?", (name,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_credential(name: str, username: str, password: str, source: str = "manual") -> int:
    """Create a new credential set. Returns the new ID."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO credentials (name, username, password, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
        (name, username, password, source, now, now),
    )
    conn.commit()
    cred_id = cursor.lastrowid
    conn.close()
    return cred_id


def update_credential(cred_id: int, name: str, username: str, password: str) -> None:
    """Update an existing credential set."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE credentials SET name = ?, username = ?, password = ?, updated_at = ? WHERE id = ?",
        (name, username, password, now, cred_id),
    )
    conn.commit()
    conn.close()


def delete_credential(cred_id: int) -> None:
    """Delete a credential set and unset it from any cameras using it."""
    conn = get_db()
    conn.execute("DELETE FROM credentials WHERE id = ?", (cred_id,))
    conn.execute("UPDATE camera_metadata SET credential_id = NULL WHERE credential_id = ?", (cred_id,))
    conn.commit()
    conn.close()


def get_cameras_using_credential(cred_id: int) -> list[str]:
    """Get list of camera names using a given credential."""
    conn = get_db()
    rows = conn.execute(
        "SELECT camera_name FROM camera_metadata WHERE credential_id = ?",
        (cred_id,),
    ).fetchall()
    conn.close()
    return [r["camera_name"] for r in rows]


def upsert_credential(name: str, username: str, password: str, source: str = "manual") -> int:
    """Insert or update a credential by name. Returns the ID."""
    conn = get_db()
    now = datetime.now(timezone.utc).isoformat()
    existing = conn.execute("SELECT id FROM credentials WHERE name = ?", (name,)).fetchone()
    if existing:
        conn.execute(
            "UPDATE credentials SET username = ?, password = ?, source = ?, updated_at = ? WHERE id = ?",
            (username, password, source, now, existing["id"]),
        )
        cred_id = existing["id"]
    else:
        cursor = conn.execute(
            "INSERT INTO credentials (name, username, password, source, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (name, username, password, source, now, now),
        )
        cred_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return cred_id
