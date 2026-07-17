"""Camera discovery routes: network scan, ONVIF probe, brand detection, stream discovery."""

from __future__ import annotations

from flask import Blueprint, render_template, request

from ..camera_discovery import (
    discover_camera,
    scan_network_range,
    scan_ports,
    verify_stream,
    _parse_scan_range,
)
from ..brand_database import get_all_brands, detect_brand_from_ports, get_brand_rtsp_urls, get_camera_indicative_ports, BRAND_DATABASE
from ..config_manager import load_config, get_cameras, get_go2rtc_streams, add_camera, save_config, deep_clone
from .. import models

bp = Blueprint("discovery", __name__)


@bp.route("/")
def discovery_page():
    """Main discovery page with scan form."""
    brands = get_all_brands()
    scan_history = models.list_scan_targets()
    credentials = models.list_credentials()
    return render_template("partials/discovery.html", brands=brands, scan_history=scan_history, credentials=credentials)


@bp.route("/scan-network", methods=["POST"])
def scan_network():
    """Scan a network range for cameras."""
    base_ip = request.form.get("base_ip", "").strip()
    if not base_ip:
        return render_template("partials/discovery_scan_results.html",
                               error="No IP address provided")

    # Validate using the range parser
    parsed = _parse_scan_range(base_ip)
    if not parsed:
        return render_template("partials/discovery_scan_results.html",
                               error="Invalid format. Use x.x.x.x, x.x.x.0, or x.x.x.100-200")

    # Save to scan history
    models.save_scan_target(base_ip)

    results = scan_network_range(base_ip)

    # Get existing camera IPs and serials to flag duplicates
    existing_ids = _get_existing_camera_ids()
    existing_ips = existing_ids["ips"]
    existing_serials = existing_ids["serials"]

    # Split into likely cameras vs possible cameras
    identifying_ports = get_camera_indicative_ports() - {554}
    likely = []
    possible = []
    for device in results:
        open_ports = set(device["open_ports"])
        has_rtsp = 554 in open_ports
        has_identifying = bool(open_ports & identifying_ports)
        device["already_added"] = device["ip"] in existing_ips
        if has_rtsp and has_identifying:
            device["confidence"] = "likely"
            likely.append(device)
        else:
            device["confidence"] = "possible"
            possible.append(device)

    return render_template("partials/discovery_scan_results.html",
                           likely=likely, possible=possible, base_ip=base_ip,
                           total=len(results))


@bp.route("/scan-history/delete", methods=["POST"])
def delete_scan_target():
    """Delete a scan target from history."""
    target = request.form.get("target", "").strip()
    if target:
        models.delete_scan_target(target)
    # Return updated dropdown
    scan_history = models.list_scan_targets()
    return render_template("partials/scan_history_dropdown.html", scan_history=scan_history)


@bp.route("/discover", methods=["POST"])
def discover():
    """Full discovery for a single camera IP."""
    ip = request.form.get("ip", "").strip()
    username = request.form.get("username", "admin").strip()
    password = request.form.get("password", "").strip()
    credential_id = request.form.get("credential_id", "").strip()

    if not ip:
        return render_template("partials/discovery_detail.html",
                               error="No IP address provided")

    result = discover_camera(ip, username, password)
    return render_template("partials/discovery_detail.html", result=result, username=username, password=password, credential_id=credential_id)


@bp.route("/probe-ports", methods=["POST"])
def probe_ports():
    """Quick port scan for a single IP."""
    ip = request.form.get("ip", "").strip()
    if not ip:
        return render_template("partials/discovery_port_results.html", error="No IP provided")

    open_ports = scan_ports(ip)
    brands = detect_brand_from_ports(open_ports)
    return render_template("partials/discovery_port_results.html",
                           ip=ip, open_ports=open_ports, brands=brands)


@bp.route("/test-stream", methods=["POST"])
def test_discovered_stream():
    """Test a specific RTSP URL from discovery."""
    url = request.form.get("url", "")
    stream_name = request.form.get("stream_name", "")
    if not url:
        return render_template("partials/test_result.html",
                               result={"success": False, "message": "No URL provided"},
                               stream_name=stream_name)

    result = verify_stream(url)
    return render_template("partials/test_result.html", result=result, stream_name=stream_name)


def _get_existing_camera_ids() -> dict[str, set[str]]:
    """Extract IP addresses and serial numbers from existing cameras.

    Returns dict with 'ips' and 'serials' sets for dedup during scan.
    """
    config = load_config()
    streams = get_go2rtc_streams(config)
    ips: set[str] = set()
    for urls in streams.values():
        for url in urls:
            if "@" in url:
                host_part = url.split("@")[1].split(":")[0].split("/")[0]
            elif "rtsp://" in url:
                host_part = url.split("rtsp://")[1].split(":")[0].split("/")[0]
            else:
                continue
            ips.add(host_part)

    # Also collect serial numbers from camera metadata
    serials: set[str] = set()
    cameras = get_cameras(config)
    for cam_name in cameras:
        meta = models.get_camera_metadata(cam_name)
        if meta and meta.get("serial_number"):
            serials.add(meta["serial_number"])

    return {"ips": ips, "serials": serials}


@bp.route("/add-camera", methods=["POST"])
def add_camera_from_discovery():
    """Add a camera from discovery results. Returns success/error notification."""
    name = request.form.get("name", "").strip()
    if not name:
        return render_template("partials/discovery_add_result.html",
                               error="Camera name is required")

    config = load_config()
    if name in get_cameras(config):
        return render_template("partials/discovery_add_result.html",
                               error=f"Camera '{name}' already exists")

    # Parse streams from form - prefix with camera name to avoid collisions
    raw_streams = {}
    i = 0
    while True:
        sname = request.form.get(f"stream_name_{i}")
        surl = request.form.get(f"stream_url_{i}")
        if sname is None and surl is None:
            break
        if sname and surl:
            raw_streams[sname.strip()] = [surl.strip()]
        i += 1

    if not raw_streams:
        return render_template("partials/discovery_add_result.html",
                               error="No streams selected")

    # Prefix stream names with camera name: main → {name}_main, sub → {name}_sub
    # This prevents overwriting generic streams from other cameras
    streams = {}
    for sname, surls in raw_streams.items():
        prefixed = f"{name}_{sname}" if not sname.startswith(f"{name}_") else sname
        streams[prefixed] = surls

    old_config = deep_clone(config)
    # Infer IP from first stream URL for webui_url
    camera_data = {}
    first_url = list(raw_streams.values())[0][0] if raw_streams else ""
    inferred_ip = ""
    if first_url:
        if "@" in first_url:
            inferred_ip = first_url.split("@")[1].split(":")[0].split("/")[0]
        elif "rtsp://" in first_url:
            inferred_ip = first_url.split("rtsp://")[1].split(":")[0].split("/")[0]
    if inferred_ip:
        camera_data["webui_url"] = f"http://{inferred_ip}"

    add_camera(config, name, camera_data, streams)
    save_config(config, description=f"Added camera from discovery: {name}")
    models.push_undo("add_camera", "cameras", name,
                     old_config.get("cameras", {}), config.get("cameras", {}))

    # Save metadata with inferred IP + ONVIF device info + credential assignment
    meta = models.get_camera_metadata(name) or {}
    if inferred_ip:
        meta["ip_address"] = inferred_ip
    # Credential ID from discovery form (if a stored credential was selected)
    cred_id = request.form.get("credential_id", "").strip()
    if cred_id:
        meta["credential_id"] = int(cred_id)
    # ONVIF device info passed from discovery form
    for field in ("manufacturer", "model", "firmware_version", "serial_number"):
        val = request.form.get(field, "").strip()
        if val:
            meta[field] = val
    models.set_camera_metadata(name, meta)

    return render_template("partials/discovery_add_result.html",
                           success=True, camera_name=name)


@bp.route("/brand-urls", methods=["POST"])
def brand_urls():
    """Get suggested RTSP URLs for a specific brand + IP + credentials."""
    brand_key = request.form.get("brand_key", "")
    ip = request.form.get("ip", "").strip()
    username = request.form.get("username", "admin").strip()
    password = request.form.get("password", "").strip()

    if not brand_key or not ip:
        return render_template("partials/discovery_brand_urls.html", error="Missing brand or IP")

    urls = get_brand_rtsp_urls(brand_key, ip, username, password)
    return render_template("partials/discovery_brand_urls.html",
                           urls=urls, brand_key=brand_key, ip=ip)


# --- Custom brand management ---

@bp.route("/brands")
def list_custom_brands():
    """List all custom/override brands."""
    custom = models.get_all_custom_brands()
    import json
    brands = []
    for row in custom:
        data = json.loads(row["brand_data"])
        brands.append({
            "key": row["brand_key"],
            "name": data.get("name", row["brand_key"]),
            "is_override": bool(row["is_override"]),
            "data": data,
        })
    return render_template("partials/custom_brands.html", custom_brands=brands)


@bp.route("/brands/add", methods=["POST"])
def add_custom_brand():
    """Add a new custom brand or override an existing one."""
    brand_key = request.form.get("brand_key", "").strip().lower().replace(" ", "_")
    brand_name = request.form.get("brand_name", "").strip()
    common_ports = request.form.get("common_ports", "").strip()
    identifying_ports = request.form.get("identifying_ports", "").strip()
    onvif_port = request.form.get("onvif_port", "").strip()
    rtsp_port = request.form.get("rtsp_port", "").strip()
    rtsp_main = request.form.get("rtsp_main", "").strip()
    rtsp_sub = request.form.get("rtsp_sub", "").strip()
    default_user = request.form.get("default_user", "admin").strip()
    default_pass = request.form.get("default_pass", "").strip()
    notes = request.form.get("notes", "").strip()
    is_override = request.form.get("is_override") is not None

    if not brand_key or not brand_name:
        return render_template("partials/custom_brands.html",
                               custom_brands=_get_custom_list(),
                               error="Brand key and name are required")

    def parse_ports(s):
        return [int(p.strip()) for p in s.split(",") if p.strip().isdigit()]

    brand_data = {
        "name": brand_name,
        "common_ports": parse_ports(common_ports),
        "identifying_ports": parse_ports(identifying_ports),
        "onvif_port": int(onvif_port) if onvif_port.isdigit() else None,
        "rtsp_port": int(rtsp_port) if rtsp_port.isdigit() else 554,
        "rtsp_url_templates": {},
        "default_credentials": {"user": default_user, "pass": default_pass},
        "suggested_settings": {"type": "generic", "ffmpeg": {"input_args": "preset-rtsp-restream"}},
        "notes": notes,
    }

    if rtsp_main:
        brand_data["rtsp_url_templates"]["main"] = rtsp_main
    if rtsp_sub:
        brand_data["rtsp_url_templates"]["sub"] = rtsp_sub

    # If overriding existing brand, only store the delta fields
    if is_override and brand_key in BRAND_DATABASE:
        override_data = {}
        if parse_ports(common_ports):
            override_data["common_ports"] = parse_ports(common_ports)
        if parse_ports(identifying_ports):
            override_data["identifying_ports"] = parse_ports(identifying_ports)
        if onvif_port.isdigit():
            override_data["onvif_port"] = int(onvif_port)
        if rtsp_port.isdigit():
            override_data["rtsp_port"] = int(rtsp_port)
        if rtsp_main:
            override_data["rtsp_url_templates"] = brand_data["rtsp_url_templates"]
        if default_pass or default_user != "admin":
            override_data["default_credentials"] = {"user": default_user, "pass": default_pass}
        if notes:
            override_data["notes"] = notes
        if brand_name:
            override_data["name"] = brand_name
        models.save_custom_brand(brand_key, override_data, is_override=True)
    else:
        models.save_custom_brand(brand_key, brand_data, is_override=False)

    return render_template("partials/custom_brands.html",
                           custom_brands=_get_custom_list(),
                           success=f"Brand '{brand_name}' saved")


@bp.route("/brands/<key>/delete", methods=["DELETE", "POST"])
def delete_custom_brand(key):
    """Delete a custom brand entry."""
    models.delete_custom_brand(key)
    return render_template("partials/custom_brands.html",
                           custom_brands=_get_custom_list(),
                           success=f"Brand '{key}' deleted")


@bp.route("/brands/<key>/edit")
def edit_custom_brand(key):
    """Get a custom brand for editing."""
    row = models.get_custom_brand(key)
    if not row:
        return render_template("partials/custom_brand_form.html", error="Brand not found")
    import json
    data = json.loads(row["brand_data"])
    return render_template("partials/custom_brand_form.html",
                           brand_key=key, brand=data,
                           is_override=bool(row["is_override"]),
                           builtin=BRAND_DATABASE.get(key))


@bp.route("/brands/add-form")
def add_brand_form():
    """Show the add custom brand form."""
    return render_template("partials/custom_brand_form.html")


def _get_custom_list():
    """Helper to get custom brand list for re-rendering."""
    import json
    custom = models.get_all_custom_brands()
    brands = []
    for row in custom:
        data = json.loads(row["brand_data"])
        brands.append({
            "key": row["brand_key"],
            "name": data.get("name", row["brand_key"]),
            "is_override": bool(row["is_override"]),
            "data": data,
        })
    return brands
