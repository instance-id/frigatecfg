"""Camera discovery: network scanning, ONVIF probing, brand detection, stream discovery."""

from __future__ import annotations

import socket
import subprocess
import json
import concurrent.futures
from typing import Any
from urllib.parse import urlparse

from .brand_database import (
    _get_all_scan_ports,
    detect_brand_from_ports,
    format_rtsp_url,
    get_brand_rtsp_urls,
    get_camera_indicative_ports,
)


def _tcp_port_open(host: str, port: int, timeout: float = 1.5) -> bool:
    """Check if a TCP port is open on a host."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((host, port)) == 0
    except Exception:
        return False
    finally:
        sock.close()


def scan_ports(host: str, ports: list[int] | None = None, timeout: float = 1.5) -> list[int]:
    """Scan common camera ports on a host. Returns list of open ports."""
    if ports is None:
        ports = _get_all_scan_ports()
    open_ports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(_tcp_port_open, host, p, timeout): p for p in ports}
        for future in concurrent.futures.as_completed(futures):
            port = futures[future]
            try:
                if future.result():
                    open_ports.append(port)
            except Exception:
                pass
    return sorted(open_ports)


def _parse_scan_range(target: str) -> tuple[str, int, int] | None:
    """Parse a scan target into (network_prefix, start_octet, end_octet).

    Supports:
      192.168.100.0       → scan 1-254
      192.168.100.1       → scan 1-254 (backwards compat, full /24)
      192.168.100.100-200 → scan 100-200
      192.168.100.100-192.168.100.200 → scan 100-200
    """
    target = target.strip()
    if "-" in target:
        parts = target.split("-")
        if len(parts) != 2:
            return None
        start_part = parts[0].strip()
        end_part = parts[1].strip()
        start_octets = start_part.split(".")
        if len(start_octets) != 4:
            return None
        network = ".".join(start_octets[:3])
        start_octet = int(start_octets[3])
        # End could be just an octet or a full IP
        if "." in end_part:
            end_octets = end_part.split(".")
            if len(end_octets) != 4:
                return None
            end_octet = int(end_octets[3])
        else:
            end_octet = int(end_part)
        if start_octet < 0 or end_octet > 255 or start_octet > end_octet:
            return None
        return (network, start_octet, end_octet)
    else:
        parts = target.split(".")
        if len(parts) != 4:
            return None
        network = ".".join(parts[:3])
        last = int(parts[3])
        # .0 or any specific IP → scan full /24
        return (network, 1, 254)


def scan_network_range(target: str, ports: list[int] | None = None, timeout: float = 1.0) -> list[dict[str, Any]]:
    """Scan a network range for devices with camera ports open.

    target: e.g. "192.168.100.0" (full /24), "192.168.100.100-200" (partial range),
            or "192.168.100.100-192.168.100.200" (explicit range).

    Only returns hosts that have at least one camera-indicative port open
    (RTSP 554 or any brand identifying port). Devices with only generic
    web ports (80, 443, 8080) are filtered out.
    """
    parsed = _parse_scan_range(target)
    if not parsed:
        return []
    network, start_octet, end_octet = parsed
    results = []

    camera_ports = get_camera_indicative_ports()

    def scan_host(octet: int) -> dict[str, Any] | None:
        ip = f"{network}.{octet}"
        open_ports = scan_ports(ip, ports=ports or _get_all_scan_ports(), timeout=timeout)
        if not open_ports:
            return None

        # Filter: must have at least one camera-indicative port
        if not any(p in camera_ports for p in open_ports):
            return None

        brands = detect_brand_from_ports(open_ports)
        return {
            "ip": ip,
            "open_ports": open_ports,
            "possible_brands": [(k, b["name"], s) for k, b, s in brands[:3]],
        }

    octets = list(range(start_octet, end_octet + 1))
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(scan_host, i): i for i in octets}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception:
                pass

    results.sort(key=lambda r: socket.inet_aton(r["ip"]))
    return results


def probe_onvif(ip: str, port: int = 80, username: str = "admin", password: str = "") -> dict[str, Any]:
    """Probe a camera via ONVIF to get device info and stream URIs.

    Returns dict with:
    - success: bool
    - device_info: {manufacturer, model, firmware, serial, hardware}
    - streams: [{name, uri, resolution, bitrate, fps}]
    - capabilities: {ptz, audio, analytics, imaging}
    - error: str (if failed)
    """
    result: dict[str, Any] = {
        "success": False,
        "device_info": {},
        "streams": [],
        "capabilities": {},
        "error": "",
    }

    try:
        from onvif import ONVIFCamera

        cam = ONVIFCamera(ip, port, username, password)

        # Device info
        dev_service = cam.devicemgmt
        dev_info = dev_service.GetDeviceInformation()
        result["device_info"] = {
            "manufacturer": getattr(dev_info, "Manufacturer", "Unknown"),
            "model": getattr(dev_info, "Model", "Unknown"),
            "firmware": getattr(dev_info, "FirmwareVersion", "Unknown"),
            "serial": getattr(dev_info, "SerialNumber", "Unknown"),
            "hardware": getattr(dev_info, "HardwareId", "Unknown"),
        }

        # Media service - get stream profiles
        media_service = cam.create_media_service()
        profiles = media_service.GetProfiles()

        for i, profile in enumerate(profiles):
            stream_info: dict[str, Any] = {
                "name": getattr(profile, "Name", f"Profile_{i}"),
                "token": getattr(profile, "token", ""),
                "uri": "",
                "resolution": "",
                "bitrate": "",
                "fps": "",
            }

            # Get resolution from video encoder config
            if hasattr(profile, "VideoEncoderConfiguration") and profile.VideoEncoderConfiguration:
                vec = profile.VideoEncoderConfiguration
                if hasattr(vec, "Resolution"):
                    w = getattr(vec.Resolution, "Width", "?")
                    h = getattr(vec.Resolution, "Height", "?")
                    stream_info["resolution"] = f"{w}x{h}"
                if hasattr(vec, "RateControl"):
                    stream_info["bitrate"] = f"{getattr(vec.RateControl, 'BitrateLimit', '?')} kbps"
                    stream_info["fps"] = f"{getattr(vec.RateControl, 'FrameRateLimit', '?')} fps"

            # Get stream URI
            try:
                req = media_service.create_type("GetStreamUri")
                req.ProfileToken = profile.token
                req.StreamSetup = {
                    "Stream": "RTP-Unicast",
                    "Transport": {"Protocol": "RTSP"},
                }
                uri_resp = media_service.GetStreamUri(req)
                stream_info["uri"] = uri_resp.Uri
            except Exception:
                pass

            result["streams"].append(stream_info)

        # Capabilities
        caps = {}

        # PTZ
        try:
            ptz_service = cam.create_ptz_service()
            nodes = ptz_service.GetNodes()
            caps["ptz"] = bool(nodes)
        except Exception:
            caps["ptz"] = False

        # Audio
        try:
            audio_sources = media_service.GetAudioSources()
            caps["audio"] = bool(audio_sources)
        except Exception:
            caps["audio"] = False

        # Analytics
        try:
            analytics_service = cam.create_analytics_service()
            analytics_service.GetSupportedAnalyticsModules()
            caps["analytics"] = True
        except Exception:
            caps["analytics"] = False

        result["capabilities"] = caps
        result["success"] = True

    except ImportError:
        result["error"] = "onvif-zeep not installed"
    except Exception as e:
        err_msg = str(e).lower()
        if "auth" in err_msg or "401" in err_msg or "unauthorized" in err_msg:
            result["error"] = "Authentication failed - check credentials"
        elif "connection" in err_msg or "refused" in err_msg:
            result["error"] = f"Connection failed to {ip}:{port}"
        elif "timeout" in err_msg or "timed out" in err_msg:
            result["error"] = f"Connection timed out to {ip}:{port}"
        else:
            result["error"] = str(e)[:200]

    return result


def verify_stream(url: str, timeout: float = 10.0) -> dict[str, Any]:
    """Verify an RTSP stream using ffprobe. Returns stream details or error."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 554
        if not host:
            return {"success": False, "message": "Invalid URL: no host found."}
    except Exception as e:
        return {"success": False, "message": f"Error parsing URL: {e}"}

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-rtsp_transport", "tcp",
                "-timeout", str(int(timeout * 1000000)),
                "-print_format", "json",
                "-show_streams",
                url,
            ],
            capture_output=True, text=True, timeout=timeout + 5,
        )

        if result.returncode == 0:
            info = json.loads(result.stdout)
            streams = info.get("streams", [])
            video_streams = [s for s in streams if s.get("codec_type") == "video"]
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

            details = []
            for vs in video_streams:
                w = vs.get("width", "?")
                h = vs.get("height", "?")
                codec = vs.get("codec_name", "?")
                fps = vs.get("avg_frame_rate", "?")
                details.append(f"{codec} {w}x{h} @ {fps}fps")
            if audio_streams:
                details.append("audio")

            return {
                "success": True,
                "message": f"Verified: {' | '.join(details)}" if details else "Stream accessible",
                "video": len(video_streams) > 0,
                "audio": len(audio_streams) > 0,
                "resolution": f"{video_streams[0].get('width','?')}x{video_streams[0].get('height','?')}" if video_streams else "",
                "codec": video_streams[0].get("codec_name", "?") if video_streams else "",
            }
        else:
            stderr = result.stderr.strip().lower()
            if "401" in stderr or "unauthorized" in stderr:
                return {"success": False, "message": "Authentication failed - check credentials"}
            if "404" in stderr or "not found" in stderr:
                return {"success": False, "message": "Stream path not found - check URL"}
            if "connection refused" in stderr:
                return {"success": False, "message": f"Connection refused by {host}:{port}"}
            if "timeout" in stderr or "timed out" in stderr:
                return {"success": False, "message": f"Connection to {host}:{port} timed out"}
            return {"success": False, "message": f"Stream test failed: {result.stderr.strip()[:150]}"}

    except subprocess.TimeoutExpired:
        return {"success": False, "message": f"Probe timed out after {timeout}s"}
    except FileNotFoundError:
        # Fallback to TCP
        if _tcp_port_open(host, port, timeout):
            return {"success": True, "message": f"TCP connect succeeded (ffprobe unavailable)", "warning": True}
        return {"success": False, "message": f"Cannot connect to {host}:{port}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


def discover_camera(ip: str, username: str = "admin", password: str = "",
                    onvif_port: int | None = None) -> dict[str, Any]:
    """Full discovery for a single camera IP.

    1. Port scan
    2. Brand detection from ports
    3. ONVIF probe (if ONVIF port found)
    4. Suggested RTSP URLs from brand database
    5. Verify suggested streams with ffprobe
    """
    result: dict[str, Any] = {
        "ip": ip,
        "open_ports": [],
        "detected_brands": [],
        "onvif": None,
        "suggested_streams": [],
        "verified_streams": [],
    }

    # 1. Port scan
    open_ports = scan_ports(ip)
    result["open_ports"] = open_ports

    if not open_ports:
        result["error"] = "No camera ports detected"
        return result

    # 2. Brand detection
    brand_matches = detect_brand_from_ports(open_ports)
    result["detected_brands"] = [
        {"key": k, "name": b["name"], "score": s,
         "onvif_port": b.get("onvif_port"),
         "rtsp_port": b.get("rtsp_port"),
         "notes": b.get("notes", "")}
        for k, b, s in brand_matches
    ]

    # 3. ONVIF probe - try detected ONVIF port, then common ports
    onvif_ports_to_try = []
    if onvif_port:
        onvif_ports_to_try.append(onvif_port)
    for brand_key, brand, _ in brand_matches:
        op = brand.get("onvif_port")
        if op and op not in onvif_ports_to_try:
            onvif_ports_to_try.append(op)
    for p in [80, 8000, 8080, 10080, 88]:
        if p in open_ports and p not in onvif_ports_to_try:
            onvif_ports_to_try.append(p)

    for op in onvif_ports_to_try:
        if op not in open_ports:
            continue
        onvif_result = probe_onvif(ip, op, username, password)
        if onvif_result["success"]:
            onvif_result["port"] = op
            result["onvif"] = onvif_result
            break
        elif "auth" in onvif_result.get("error", "").lower():
            # Auth failed - stop trying, user needs correct creds
            onvif_result["port"] = op
            result["onvif"] = onvif_result
            break

    # 4. Suggested RTSP URLs from brand database
    suggested = []
    if brand_matches:
        top_brand_key = brand_matches[0][0]
        brand = brand_matches[0][1]
        rtsp_urls = get_brand_rtsp_urls(top_brand_key, ip, username, password)
        for stream_type, url in rtsp_urls.items():
            suggested.append({
                "stream_type": stream_type,
                "url": url,
                "brand": brand["name"],
                "source": "brand_template",
            })

    # Also add ONVIF-discovered streams
    if result["onvif"] and result["onvif"].get("streams"):
        for s in result["onvif"]["streams"]:
            if s.get("uri"):
                suggested.append({
                    "stream_type": s["name"],
                    "url": s["uri"],
                    "resolution": s.get("resolution", ""),
                    "brand": "ONVIF",
                    "source": "onvif",
                })

    result["suggested_streams"] = suggested

    # 5. Verify suggested streams
    verified = []
    for s in suggested:
        v = verify_stream(s["url"])
        verified.append({
            "stream_type": s["stream_type"],
            "url": s["url"],
            "source": s["source"],
            "verified": v["success"],
            "message": v.get("message", ""),
            "resolution": v.get("resolution", s.get("resolution", "")),
            "codec": v.get("codec", ""),
            "warning": v.get("warning", False),
        })
    result["verified_streams"] = verified

    return result
