"""Main routes: dashboard, config overview, version history."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from .. import models
from ..config_manager import load_config, get_cameras, get_go2rtc_streams, build_camera_streams_map
from ..config_schema import SECTION_GROUPS, ALL_SECTIONS, SECTION_MAP
from ..docker_manager import get_frigate_status

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    config = load_config()
    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    status = get_frigate_status()
    versions = models.list_versions(limit=10)
    total_versions = versions[0]["version"] if versions else 0
    can_undo = models.can_undo()
    can_redo = models.can_redo()
    camera_streams = build_camera_streams_map(config)

    return render_template(
        "index.html",
        config=config,
        cameras=cameras,
        streams=streams,
        camera_streams=camera_streams,
        section_groups=SECTION_GROUPS,
        all_sections=ALL_SECTIONS,
        section_map=SECTION_MAP,
        frigate_status=status,
        versions=versions,
        total_versions=total_versions,
        can_undo=can_undo,
        can_redo=can_redo,
    )


@bp.route("/dashboard")
def dashboard():
    """HTMX partial: main dashboard content."""
    config = load_config()
    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    status = get_frigate_status()
    versions = models.list_versions(limit=10)
    total_versions = versions[0]["version"] if versions else 0
    camera_streams = build_camera_streams_map(config)

    return render_template(
        "partials/dashboard.html",
        config=config,
        cameras=cameras,
        streams=streams,
        camera_streams=camera_streams,
        frigate_status=status,
        versions=versions,
        total_versions=total_versions,
    )


@bp.route("/versions")
def versions():
    """HTMX partial: version history."""
    versions = models.list_versions(limit=50)
    return render_template("partials/versions.html", versions=versions)
