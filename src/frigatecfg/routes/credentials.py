"""Credentials routes: list, create, update, delete stored credential sets."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from .. import models
from ..config_manager import (
    load_config, save_config, deep_clone,
    apply_credentials_to_camera_streams,
)

bp = Blueprint("credentials", __name__)


@bp.route("/")
def credentials_page():
    """HTMX partial: credentials management page."""
    creds = models.list_credentials()
    # Count cameras using each credential
    for cred in creds:
        cred["camera_count"] = len(models.get_cameras_using_credential(cred["id"]))
    return render_template("partials/credentials.html", credentials=creds)


@bp.route("/", methods=["POST"])
def create_credential():
    """Create a new credential set."""
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not username:
        return render_template("partials/credentials.html",
                               credentials=_creds_with_counts(),
                               error="Name and username are required")

    existing = models.get_credential_by_name(name)
    if existing:
        return render_template("partials/credentials.html",
                               credentials=_creds_with_counts(),
                               error=f"Credential '{name}' already exists")

    models.create_credential(name, username, password)
    return render_template("partials/credentials.html",
                           credentials=_creds_with_counts(),
                           success=f"Created credential: {name}")


@bp.route("/<int:cred_id>", methods=["POST"])
def update_credential(cred_id: int):
    """Update an existing credential set."""
    cred = models.get_credential(cred_id)
    if not cred:
        return render_template("partials/credentials.html",
                               credentials=_creds_with_counts(),
                               error="Credential not found")

    if cred["source"] == "env":
        return render_template("partials/credentials.html",
                               credentials=_creds_with_counts(),
                               error="Env-sourced credentials are read-only")

    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()

    if not name or not username:
        return render_template("partials/credentials.html",
                               credentials=_creds_with_counts(),
                               error="Name and username are required")

    models.update_credential(cred_id, name, username, password)

    # Propagate credential changes to all cameras using this credential
    camera_names = models.get_cameras_using_credential(cred_id)
    updated_cameras = []
    if camera_names:
        config = load_config()
        old_config = deep_clone(config)
        for cam_name in camera_names:
            updated = apply_credentials_to_camera_streams(config, cam_name, username, password)
            if updated:
                updated_cameras.append(cam_name)
        if updated_cameras:
            save_config(config, description=f"Propagated credential update '{name}' to: {', '.join(updated_cameras)}")

    success_msg = f"Updated credential: {name}"
    if updated_cameras:
        success_msg += f" — also updated {len(updated_cameras)} camera(s): {', '.join(updated_cameras)}"

    return render_template("partials/credentials.html",
                           credentials=_creds_with_counts(),
                           success=success_msg)


@bp.route("/<int:cred_id>", methods=["DELETE"])
def delete_credential(cred_id: int):
    """Delete a credential set."""
    cred = models.get_credential(cred_id)
    if not cred:
        return render_template("partials/credentials.html",
                               credentials=_creds_with_counts(),
                               error="Credential not found")

    if cred["source"] == "env":
        return render_template("partials/credentials.html",
                               credentials=_creds_with_counts(),
                               error="Env-sourced credentials are read-only")

    name = cred["name"]
    models.delete_credential(cred_id)
    return render_template("partials/credentials.html",
                           credentials=_creds_with_counts(),
                           success=f"Deleted credential: {name}")


def _creds_with_counts() -> list[dict]:
    """Helper: list credentials with camera usage counts."""
    creds = models.list_credentials()
    for cred in creds:
        cred["camera_count"] = len(models.get_cameras_using_credential(cred["id"]))
    return creds
