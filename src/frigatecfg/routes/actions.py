"""Action routes: restart frigate, undo/redo, version restore."""

from __future__ import annotations

import json

from flask import Blueprint, render_template, request

from .. import models
from ..config_manager import load_config, save_config, deep_clone, get_config_path
from ..docker_manager import restart_frigate, get_frigate_status
from ..config_schema import SECTION_GROUPS, ALL_SECTIONS, SECTION_MAP

bp = Blueprint("actions", __name__)


@bp.route("/restart", methods=["POST"])
def restart():
    result = restart_frigate()
    return render_template("partials/action_result.html", result=result, action="restart")


@bp.route("/status")
def status():
    """HTMX partial: frigate container status."""
    status = get_frigate_status()
    return render_template("partials/status.html", status=status)


@bp.route("/undo", methods=["POST"])
def undo():
    entry = models.pop_undo()
    if not entry:
        return render_template("partials/action_result.html", result={"success": False, "message": "Nothing to undo."}, action="undo")

    config = load_config()
    section = entry.get("section")
    old_state = entry.get("old_state")

    if section and old_state is not None:
        config[section] = old_state
        save_config(config, description=f"Undo: {entry.get('action', 'unknown')}")

    can_undo = models.can_undo()
    can_redo = models.can_redo()
    return render_template("partials/action_result.html", result={"success": True, "message": "Undone."}, action="undo", can_undo=can_undo, can_redo=can_redo)


@bp.route("/redo", methods=["POST"])
def redo():
    entry = models.pop_redo()
    if not entry:
        return render_template("partials/action_result.html", result={"success": False, "message": "Nothing to redo."}, action="redo")

    config = load_config()
    section = entry.get("section")
    new_state = entry.get("new_state")

    if section and new_state is not None:
        config[section] = new_state
        save_config(config, description=f"Redo: {entry.get('action', 'unknown')}")

    can_undo = models.can_undo()
    can_redo = models.can_redo()
    return render_template("partials/action_result.html", result={"success": True, "message": "Redone."}, action="redo", can_undo=can_undo, can_redo=can_redo)


@bp.route("/restore/<int:version>", methods=["POST"])
def restore_version(version):
    v = models.get_version(version)
    if not v:
        return render_template("partials/action_result.html", result={"success": False, "message": f"Version {version} not found."}, action="restore")

    config = json.loads(v["config_json"])
    old_config = deep_clone(load_config())
    save_config(config, description=f"Restored version {version}")
    models.push_undo("restore_version", None, None, old_config, config)

    return render_template("partials/action_result.html", result={"success": True, "message": f"Restored version {version}."}, action="restore")


@bp.route("/export")
def export():
    """Download current config as YAML."""
    from flask import Response
    config = load_config()
    from ..config_manager import dump_yaml
    yaml_str = dump_yaml(config)
    return Response(yaml_str, mimetype="text/yaml", headers={"Content-Disposition": "attachment; filename=config.yml"})
