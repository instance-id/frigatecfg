"""Camera routes: list, create, edit, delete, reorder, stream management."""

from __future__ import annotations

import copy

from flask import Blueprint, render_template, request, redirect, url_for, flash

from .. import models
from ..config_manager import (
    load_config, save_config, get_cameras, get_camera, get_camera_streams,
    add_camera, rename_camera, delete_camera, update_camera_streams,
    reorder_cameras, get_go2rtc_streams, deep_clone,
    apply_credentials_to_camera_streams, build_camera_streams_map,
)
from ..config_schema import CAMERA_FIELDS, CAMERA_OVERRIDE_SECTIONS, SECTION_MAP
from ..docker_manager import test_rtsp_connection
from ..camera_discovery import discover_camera

bp = Blueprint("cameras", __name__)


def _extract_ip_from_url(url: str) -> str:
    """Extract IP address from an RTSP URL.

    e.g. rtsp://admin:pass@192.168.1.100:554/path → 192.168.1.100
    """
    if not url:
        return ""
    try:
        if "@" in url:
            host_part = url.split("@")[1].split(":")[0].split("/")[0]
        elif "rtsp://" in url:
            host_part = url.split("rtsp://")[1].split(":")[0].split("/")[0]
        elif "http://" in url:
            host_part = url.split("http://")[1].split(":")[0].split("/")[0]
        elif "https://" in url:
            host_part = url.split("https://")[1].split(":")[0].split("/")[0]
        else:
            return ""
        # Validate it looks like an IP
        parts = host_part.split(".")
        if len(parts) == 4 and all(p.isdigit() for p in parts):
            return host_part
        return ""
    except (IndexError, ValueError):
        return ""


@bp.route("/")
def camera_list():
    """HTMX partial: camera list."""
    config = load_config()
    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    camera_streams = build_camera_streams_map(config)
    return render_template("partials/camera_list.html", cameras=cameras, config=config, streams=streams, camera_streams=camera_streams)


@bp.route("/new")
def new_camera_form():
    """HTMX partial: new camera form."""
    return render_template("partials/camera_form.html", camera=None, streams={}, is_new=True)


@bp.route("/", methods=["POST"])
def create_camera():
    name = request.form.get("name", "").strip()
    if not name:
        return render_template("partials/camera_form.html", camera=None, streams={}, is_new=True, error="Camera name is required.")

    config = load_config()
    if name in get_cameras(config):
        return render_template("partials/camera_form.html", camera=None, streams={}, is_new=True, error=f"Camera '{name}' already exists.")

    # Parse streams from form
    streams = parse_streams_from_form(request.form)
    stream_roles = parse_stream_roles_from_form(request.form)

    # Parse camera data
    camera_data = parse_camera_from_form(request.form)

    old_config = deep_clone(config)
    add_camera(config, name, camera_data, streams, stream_roles)
    save_config(config, description=f"Added camera: {name}")
    models.push_undo("add_camera", "cameras", name, old_config.get("cameras", {}), config.get("cameras", {}))

    # Save metadata to DB
    metadata = parse_metadata_from_form(request.form)
    models.set_camera_metadata(name, metadata)

    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    camera_streams = build_camera_streams_map(config)
    return render_template("partials/camera_list.html", cameras=cameras, config=config, streams=streams, camera_streams=camera_streams)


@bp.route("/<name>")
def edit_camera(name):
    """HTMX partial: camera editor."""
    config = load_config()
    camera = get_camera(config, name)
    if not camera:
        return render_template("partials/error.html", message=f"Camera '{name}' not found.")

    streams = get_camera_streams(config, name)
    all_streams = get_go2rtc_streams(config)
    metadata = models.get_camera_metadata(name) or {}

    # Infer camera IP from first stream URL
    inferred_ip = ""
    for surls in streams.values():
        if surls:
            inferred_ip = _extract_ip_from_url(surls[0])
            if inferred_ip:
                break

    # Auto-populate webui_url if not set
    if not camera.get("webui_url") and inferred_ip:
        camera = dict(camera)  # copy to avoid mutating config
        camera["webui_url"] = f"http://{inferred_ip}"

    # Auto-populate metadata IP if not set
    if not metadata.get("ip_address") and inferred_ip:
        metadata = dict(metadata)
        metadata["ip_address"] = inferred_ip

    # Build stream_roles map from existing ffmpeg inputs
    stream_roles = {}
    for inp in camera.get("ffmpeg", {}).get("inputs", []):
        path = inp.get("path", "")
        if "127.0.0.1:8554/" in path:
            stream_name = path.split("127.0.0.1:8554/")[1].split("?")[0]
            roles = inp.get("roles", [])
            stream_roles[stream_name] = roles[0] if roles else "record"

    # Current live stream name (from live.streams dict — first value)
    live_streams = camera.get("live", {}).get("streams", {})
    live_stream_name = list(live_streams.values())[0] if live_streams else ""

    # Current record output preset (camera-level override)
    record_output_preset = camera.get("ffmpeg", {}).get("output_args", {}).get("record", "")

    return render_template(
        "partials/camera_editor.html",
        camera_name=name,
        camera=camera,
        streams=streams,
        stream_roles=stream_roles,
        live_stream_name=live_stream_name,
        record_output_preset=record_output_preset,
        camera_fields=CAMERA_FIELDS,
        override_sections=CAMERA_OVERRIDE_SECTIONS,
        section_map=SECTION_MAP,
        metadata=metadata,
        credentials=models.list_credentials(),
    )


@bp.route("/<name>", methods=["POST"])
def update_camera_route(name):
    config = load_config()
    camera = get_camera(config, name)
    if not camera:
        return render_template("partials/error.html", message=f"Camera '{name}' not found.")

    old_config = deep_clone(config)

    # Check for rename
    new_name = request.form.get("name", "").strip()
    if new_name and new_name != name:
        if new_name in get_cameras(config):
            return render_template("partials/error.html", message=f"Camera '{new_name}' already exists.")
        rename_camera(config, name, new_name)
        models.rename_camera_metadata(name, new_name)
        name = new_name

    # Parse streams — always update, even if empty, to sync ffmpeg inputs
    streams = parse_streams_from_form(request.form)
    stream_roles = parse_stream_roles_from_form(request.form)
    if streams:
        update_camera_streams(config, name, streams, stream_roles)

    # Merge form data into existing camera config (preserve fields not in form)
    camera = get_camera(config, name)
    camera_data = parse_camera_from_form(request.form)
    # Deep-merge live dict to preserve other live settings (height, quality, etc.)
    if "live" in camera_data and "live" in camera:
        camera["live"].update(camera_data.pop("live"))
    # Deep-merge ffmpeg.output_args to preserve other ffmpeg settings
    if "ffmpeg" in camera_data and "ffmpeg" in camera:
        cam_ff = camera_data["ffmpeg"]
        existing_ff = camera["ffmpeg"]
        if "output_args" in cam_ff and "output_args" in existing_ff:
            existing_ff["output_args"].update(cam_ff.pop("output_args"))
        existing_ff.update(cam_ff)
        camera_data.pop("ffmpeg")
    # Deep-merge record dict to preserve nested settings (alerts, detections, retain)
    if "record" in camera_data and "record" in camera:
        existing_record = camera["record"]
        new_record = camera_data["record"]
        for key in ("alerts", "detections", "retain"):
            if key in new_record and key in existing_record:
                existing_record[key].update(new_record.pop(key))
        existing_record.update(new_record)
        camera_data.pop("record")
    # Deep-merge detect dict to preserve nested settings (stationary)
    if "detect" in camera_data and "detect" in camera:
        existing_detect = camera["detect"]
        new_detect = camera_data["detect"]
        if "stationary" in new_detect and "stationary" in existing_detect:
            existing_detect["stationary"].update(new_detect.pop("stationary"))
        existing_detect.update(new_detect)
        camera_data.pop("detect")
    # Deep-merge snapshots dict to preserve nested settings (retain)
    if "snapshots" in camera_data and "snapshots" in camera:
        existing_snap = camera["snapshots"]
        new_snap = camera_data["snapshots"]
        if "retain" in new_snap and "retain" in existing_snap:
            existing_snap["retain"].update(new_snap.pop("retain"))
        existing_snap.update(new_snap)
        camera_data.pop("snapshots")
    camera.update(camera_data)
    # Remove fields that were explicitly unset (e.g. toggles turned off)
    # but keep ffmpeg.inputs which is managed by update_camera_streams

    save_config(config, description=f"Updated camera: {name}")
    models.push_undo("update_camera", "cameras", name, old_config.get("cameras", {}), config.get("cameras", {}))

    # Save metadata to DB (not Frigate config)
    metadata = parse_metadata_from_form(request.form)
    models.set_camera_metadata(name, metadata)

    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    camera_streams = build_camera_streams_map(config)
    return render_template("partials/camera_list.html", cameras=cameras, config=config, streams=streams, camera_streams=camera_streams)


@bp.route("/<name>", methods=["DELETE"])
def delete_camera_route(name):
    config = load_config()
    old_config = deep_clone(config)
    delete_camera(config, name)
    save_config(config, description=f"Deleted camera: {name}")
    models.push_undo("delete_camera", "cameras", name, old_config.get("cameras", {}), config.get("cameras", {}))
    models.delete_camera_metadata(name)

    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    return render_template("partials/camera_list.html", cameras=cameras, config=config, streams=streams)


@bp.route("/reorder", methods=["POST"])
def reorder():
    order = request.form.getlist("camera_order")
    config = load_config()
    old_config = deep_clone(config)
    reorder_cameras(config, order)
    save_config(config, description="Reordered cameras")
    models.push_undo("reorder_cameras", "cameras", None, old_config.get("cameras", {}), config.get("cameras", {}))

    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    camera_streams = build_camera_streams_map(config)
    return render_template("partials/camera_list.html", cameras=cameras, config=config, streams=streams, camera_streams=camera_streams)


@bp.route("/test-stream", methods=["POST"])
def test_stream():
    url = request.form.get("url", "")
    stream_name = request.form.get("stream_name", "")
    if not url:
        return render_template("partials/test_result.html", result={"success": False, "message": "No URL provided."}, stream_name=stream_name)

    result = test_rtsp_connection(url)
    return render_template("partials/test_result.html", result=result, stream_name=stream_name)


def parse_streams_from_form(form) -> dict[str, list[str]]:
    """Parse stream definitions from form data.

    Form fields: stream_name_0, stream_url_0, stream_role_0, stream_name_1, etc.
    """
    streams = {}
    i = 0
    while True:
        sname = form.get(f"stream_name_{i}")
        surl = form.get(f"stream_url_{i}")
        if sname is None and surl is None:
            break
        if sname and surl:
            streams[sname.strip()] = [surl.strip()]
        i += 1
    return streams


def parse_stream_roles_from_form(form) -> dict[str, str]:
    """Parse stream role mappings from form data.

    Returns dict of stream_name -> role (e.g. {"front_door": "record", "front_door_sub": "detect"}).
    """
    roles = {}
    i = 0
    while True:
        sname = form.get(f"stream_name_{i}")
        srole = form.get(f"stream_role_{i}")
        if sname is None and srole is None:
            break
        if sname and srole:
            roles[sname.strip()] = srole.strip()
        i += 1
    return roles


def parse_camera_from_form(form) -> dict:
    """Parse camera configuration from form data."""
    camera = {}

    # Basic fields — checkboxes don't send values when unchecked, so always set
    camera["enabled"] = form.get("enabled") is not None

    cam_type = form.get("type")
    if cam_type:
        camera["type"] = cam_type

    # UI order
    order = form.get("ui_order")
    if order is not None:
        camera["ui"] = {"order": int(order) if order else 0}

    # Objects
    track = form.getlist("objects_track")
    if track:
        camera["objects"] = {"track": track}

    # Record — always set (checkbox)
    camera["record"] = {"enabled": form.get("record_enabled") is not None}
    if camera["record"]["enabled"]:
        record = camera["record"]

        # Retain settings
        retain_days = form.get("record_retain_days")
        retain_mode = form.get("record_retain_mode", "").strip()
        if retain_days is not None:
            record["retain"] = {"days": int(retain_days) if retain_days else 0}
            if retain_mode:
                record["retain"]["mode"] = retain_mode

        # Expire interval
        expire_interval = form.get("record_expire_interval")
        if expire_interval:
            record["expire_interval"] = int(expire_interval)

        # Alerts recording settings
        alerts_pre = form.get("record_alerts_pre")
        alerts_post = form.get("record_alerts_post")
        alerts_retain_days = form.get("record_alerts_retain_days")
        alerts_retain_mode = form.get("record_alerts_retain_mode", "").strip()
        if any([alerts_pre, alerts_post, alerts_retain_days, alerts_retain_mode]):
            alerts = {}
            if alerts_pre:
                alerts["pre_capture"] = int(alerts_pre)
            if alerts_post:
                alerts["post_capture"] = int(alerts_post)
            if alerts_retain_days:
                alerts["retain"] = {"days": int(alerts_retain_days)}
                if alerts_retain_mode:
                    alerts["retain"]["mode"] = alerts_retain_mode
            record["alerts"] = alerts

        # Detections recording settings
        det_pre = form.get("record_detections_pre")
        det_post = form.get("record_detections_post")
        det_retain_days = form.get("record_detections_retain_days")
        det_retain_mode = form.get("record_detections_retain_mode", "").strip()
        if any([det_pre, det_post, det_retain_days, det_retain_mode]):
            detections = {}
            if det_pre:
                detections["pre_capture"] = int(det_pre)
            if det_post:
                detections["post_capture"] = int(det_post)
            if det_retain_days:
                detections["retain"] = {"days": int(det_retain_days)}
                if det_retain_mode:
                    detections["retain"]["mode"] = det_retain_mode
            record["detections"] = detections

    # Detect — always set (checkbox) + detect config
    detect = {"enabled": form.get("detect_enabled") is not None}
    detect_width = form.get("detect_width", "").strip()
    detect_height = form.get("detect_height", "").strip()
    detect_fps = form.get("detect_fps", "").strip()
    detect_min_init = form.get("detect_min_initialized", "").strip()
    detect_max_disp = form.get("detect_max_disappeared", "").strip()
    if detect_width:
        detect["width"] = int(detect_width)
    if detect_height:
        detect["height"] = int(detect_height)
    if detect_fps:
        detect["fps"] = int(detect_fps)
    if detect_min_init:
        detect["min_initialized"] = int(detect_min_init)
    if detect_max_disp:
        detect["max_disappeared"] = int(detect_max_disp)
    # Stationary settings
    stat_threshold = form.get("detect_stationary_threshold", "").strip()
    stat_interval = form.get("detect_stationary_interval", "").strip()
    if stat_threshold or stat_interval:
        stationary = {}
        if stat_threshold:
            stationary["threshold"] = int(stat_threshold)
        if stat_interval:
            stationary["interval"] = int(stat_interval)
        detect["stationary"] = stationary
    camera["detect"] = detect

    # Snapshots — enabled checkbox + config
    snapshots = {"enabled": form.get("snapshots_enabled") is not None}
    if snapshots["enabled"]:
        if form.get("snapshots_clean_copy") is not None:
            snapshots["clean_copy"] = True
        else:
            snapshots["clean_copy"] = False
        snapshots["timestamp"] = form.get("snapshots_timestamp") is not None
        snapshots["bounding_box"] = form.get("snapshots_bounding_box") is not None
        snapshots["crop"] = form.get("snapshots_crop") is not None
        snap_height = form.get("snapshots_height", "").strip()
        if snap_height:
            snapshots["height"] = int(snap_height)
        snap_quality = form.get("snapshots_quality", "").strip()
        if snap_quality:
            snapshots["quality"] = int(snap_quality)
        snap_retain = form.get("snapshots_retain_days", "").strip()
        if snap_retain:
            snapshots["retain"] = {"default": int(snap_retain)}
    camera["snapshots"] = snapshots

    # WebUI URL
    webui_url = form.get("webui_url")
    if webui_url:
        camera["webui_url"] = webui_url

    # Best image timeout
    best_timeout = form.get("best_image_timeout")
    if best_timeout:
        camera["best_image_timeout"] = int(best_timeout)

    # Live view stream — Frigate uses live.streams dict (label → go2rtc stream name)
    live_stream = form.get("live_stream_name", "").strip()
    if live_stream:
        camera["live"] = {"streams": {live_stream: live_stream}}

    # Record output preset — camera-level ffmpeg.output_args.record override
    record_preset = form.get("record_output_preset", "").strip()
    if record_preset:
        camera.setdefault("ffmpeg", {}).setdefault("output_args", {})["record"] = record_preset

    return camera


def parse_metadata_from_form(form) -> dict:
    """Parse camera metadata (DB-only, not Frigate config) from form data."""
    cred_id = form.get("credential_id", "").strip()
    # "manual" is a sentinel value, not a real credential ID
    if cred_id == "manual":
        cred_id = None
    return {
        "notes": form.get("meta_notes", ""),
        "location": form.get("meta_location", ""),
        "ip_address": form.get("meta_ip_address", ""),
        "manufacturer": form.get("meta_manufacturer", ""),
        "model": form.get("meta_model", ""),
        "purchase_date": form.get("meta_purchase_date", ""),
        "firmware_version": form.get("meta_firmware_version", ""),
        "serial_number": form.get("meta_serial_number", ""),
        "credential_id": int(cred_id) if cred_id and cred_id.isdigit() else None,
        "manual_username": form.get("manual_username", ""),
        "manual_password": form.get("manual_password", ""),
    }


def _resolve_credentials(form) -> tuple[str, str] | None:
    """Resolve username/password from form data.

    Checks credential_id (stored credential) or manual_username/manual_password.
    Returns (username, password) or None if no credentials provided.
    """
    cred_id = form.get("credential_id", "").strip()
    if cred_id and cred_id != "manual" and cred_id.isdigit():
        cred = models.get_credential(int(cred_id))
        if cred:
            return cred["username"], cred["password"]

    manual_user = form.get("manual_username", "").strip()
    manual_pass = form.get("manual_password", "").strip()
    if manual_user:
        return manual_user, manual_pass

    return None


@bp.route("/<name>/apply-credentials", methods=["POST"])
def apply_credentials(name):
    """Apply credentials to all go2rtc stream URLs for this camera."""
    config = load_config()
    camera = get_camera(config, name)
    if not camera:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": f"Camera '{name}' not found."})

    creds = _resolve_credentials(request.form)
    if not creds:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": "No credentials selected. Choose a credential set or enter manual credentials."})

    username, password = creds
    old_config = deep_clone(config)
    updated_streams = apply_credentials_to_camera_streams(config, name, username, password)

    if updated_streams:
        save_config(config, description=f"Applied credentials to {name} streams: {', '.join(updated_streams)}")
        models.push_undo("update_camera", "cameras", name,
                         old_config.get("cameras", {}), config.get("cameras", {}))
        # Reload config for OOB stream rows swap
        config = load_config()
        cam_streams = get_camera_streams(config, name)
        cam = get_camera(config, name)
        sr = {}
        for inp in cam.get("ffmpeg", {}).get("inputs", []):
            path = inp.get("path", "")
            if "127.0.0.1:8554/" in path:
                sn = path.split("127.0.0.1:8554/")[1].split("?")[0]
                roles = inp.get("roles", [])
                sr[sn] = roles[0] if roles else "record"
        result_html = render_template("partials/test_result.html",
                               result={"success": True, "message": f"Updated {len(updated_streams)} stream(s): {', '.join(updated_streams)}"})
        stream_rows_html = render_template("partials/stream_rows.html",
                                           streams=cam_streams, stream_roles=sr)
        return result_html + stream_rows_html
    else:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": "No go2rtc streams found for this camera."})


@bp.route("/<name>/rediscover-streams", methods=["POST"])
def rediscover_streams(name):
    """Re-run stream discovery for this camera using its credentials."""
    config = load_config()
    camera = get_camera(config, name)
    if not camera:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": f"Camera '{name}' not found."})

    creds = _resolve_credentials(request.form)
    if not creds:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": "No credentials selected. Choose a credential set or enter manual credentials."})

    username, password = creds

    # Get IP from metadata or infer from current stream URLs
    meta = models.get_camera_metadata(name) or {}
    ip = meta.get("ip_address", "")
    if not ip:
        # Try to infer from existing streams
        camera_streams = get_camera_streams(config, name)
        for urls in camera_streams.values():
            for url in urls:
                if "rtsp://" in url:
                    rest = url.split("rtsp://", 1)[1]
                    if "@" in rest:
                        rest = rest.split("@", 1)[1]
                    ip = rest.split(":")[0].split("/")[0]
                    break
            if ip:
                break

    if not ip:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": f"No IP address found for this camera. Set it in Camera Notes & Details below, or ensure existing stream URLs contain an IP address."})

    result = discover_camera(ip, username, password)

    if not result.get("verified_streams"):
        return render_template("partials/test_result.html",
                               result={"success": False, "message": f"No streams found at {ip}. Ports scanned: {', '.join(map(str, result.get('open_ports', []))) or 'none open'}. Check credentials and network connectivity."})

    # Build new streams dict from verified streams, prefixed with camera name
    new_streams = {}
    stream_roles = {}
    for vs in result["verified_streams"]:
        if not vs.get("verified"):
            continue
        stream_type = vs["stream_type"]
        # Prefix with camera name to avoid collisions
        prefixed = f"{name}_{stream_type}" if not stream_type.startswith(f"{name}_") else stream_type
        new_streams[prefixed] = [vs["url"]]
        # Sub streams → detect, main streams → record
        stream_roles[prefixed] = "detect" if "sub" in stream_type.lower() else "record"

    if not new_streams:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": f"Streams were found at {ip} but none could be verified with ffprobe. The camera may require different credentials or stream paths."})

    old_config = deep_clone(config)
    update_camera_streams(config, name, new_streams, stream_roles)
    save_config(config, description=f"Re-discovered streams for {name} at {ip}")
    models.push_undo("update_camera", "cameras", name,
                     old_config.get("cameras", {}), config.get("cameras", {}))

    # Update camera metadata with ONVIF device info if discovered
    onvif = result.get("onvif")
    if onvif and onvif.get("success"):
        meta = models.get_camera_metadata(name) or {}
        meta["ip_address"] = ip
        dev = onvif.get("device_info", {})
        if dev.get("manufacturer"):
            meta["manufacturer"] = dev["manufacturer"]
        if dev.get("model"):
            meta["model"] = dev["model"]
        if dev.get("firmware"):
            meta["firmware_version"] = dev["firmware"]
        if dev.get("serial"):
            meta["serial_number"] = dev["serial"]
        # Preserve existing credential assignment
        models.set_camera_metadata(name, meta)

    stream_names = list(new_streams.keys())
    # Build detailed success message
    onvif = result.get("onvif")
    parts = [f"Found {len(stream_names)} verified stream(s): {', '.join(stream_names)}"]
    if onvif and onvif.get("success"):
        dev = onvif.get("device_info", {})
        dev_parts = []
        if dev.get("manufacturer"):
            dev_parts.append(dev["manufacturer"])
        if dev.get("model"):
            dev_parts.append(dev["model"])
        if dev_parts:
            parts.append(f"ONVIF device: {' '.join(dev_parts)}")
        if dev.get("serial"):
            parts.append(f"Serial: {dev['serial']}")
        parts.append("Camera metadata updated (manufacturer, model, firmware, serial)")
    else:
        parts.append("ONVIF not available — metadata not updated")
    parts.append(f"go2rtc streams + ffmpeg inputs replaced for {name}")

    # Reload config to get updated streams + ffmpeg inputs for OOB swap
    config = load_config()
    updated_streams = get_camera_streams(config, name)
    all_streams = get_go2rtc_streams(config)
    # Build stream_roles from ffmpeg inputs
    camera = get_camera(config, name)
    sr = {}
    for inp in camera.get("ffmpeg", {}).get("inputs", []):
        path = inp.get("path", "")
        if "127.0.0.1:8554/" in path:
            sn = path.split("127.0.0.1:8554/")[1].split("?")[0]
            roles = inp.get("roles", [])
            sr[sn] = roles[0] if roles else "record"

    result_html = render_template("partials/test_result.html",
                           result={"success": True, "message": " | ".join(parts)})
    stream_rows_html = render_template("partials/stream_rows.html",
                                       streams=updated_streams, stream_roles=sr)
    return result_html + stream_rows_html
