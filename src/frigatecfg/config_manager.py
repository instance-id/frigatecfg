"""Config manager: load, save, and manipulate Frigate YAML config.

Handles the linkage between go2rtc streams and camera ffmpeg inputs.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any
from urllib.parse import quote

import yaml

from . import models


def get_config_path() -> Path:
    env_path = os.environ.get("FRIGATE_CONFIG_PATH")
    if env_path:
        return Path(env_path)
    # Fall back to project-local config.yml for dev, /config/config.yml for Docker
    docker_path = Path("/config/config.yml")
    local_path = Path(__file__).parent.parent.parent / "config.yml"
    return docker_path if docker_path.parent.exists() else local_path


def load_config() -> dict[str, Any]:
    path = get_config_path()
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or {}


def save_config(config: dict[str, Any], description: str = "") -> int:
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    yaml_str = dump_yaml(config)
    path.write_text(yaml_str)
    return models.save_version(yaml_str, config, description)


def dump_yaml(config: dict[str, Any]) -> str:
    return yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True, width=120)


def get_section(config: dict[str, Any], section_name: str) -> dict[str, Any] | Any:
    return config.get(section_name)


def set_section(config: dict[str, Any], section_name: str, value: Any) -> None:
    if value is None or (isinstance(value, dict) and not value):
        config.pop(section_name, None)
    else:
        config[section_name] = value


# --- Camera entity management ---

def get_cameras(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("cameras", {})


def get_camera(config: dict[str, Any], name: str) -> dict[str, Any] | None:
    return config.get("cameras", {}).get(name)


def get_go2rtc_streams(config: dict[str, Any]) -> dict[str, Any]:
    return config.get("go2rtc", {}).get("streams", {})


def get_camera_streams(config: dict[str, Any], camera_name: str) -> dict[str, list[str]]:
    """Get go2rtc streams associated with a camera.

    Streams are associated by naming convention: {camera_name} and {camera_name}_sub.
    Also checks for streams explicitly referenced in ffmpeg inputs.
    """
    streams = get_go2rtc_streams(config)
    camera = get_camera(config, camera_name)
    if not camera:
        return {}

    associated = {}

    # Find streams referenced in ffmpeg inputs
    for inp in camera.get("ffmpeg", {}).get("inputs", []):
        path = inp.get("path", "")
        if "127.0.0.1:8554/" in path:
            stream_name = path.split("127.0.0.1:8554/")[1].split("?")[0]
            if stream_name in streams:
                associated[stream_name] = streams[stream_name]

    # Also check by naming convention
    for candidate in [camera_name, f"{camera_name}_sub", f"{camera_name}_main"]:
        if candidate in streams and candidate not in associated:
            associated[candidate] = streams[candidate]

    return associated


def build_camera_streams_map(config: dict[str, Any]) -> dict[str, list[str]]:
    """Map each camera name to its stream names using longest-prefix match.

    Prevents 'kitchen' from claiming 'kitchen_door' streams.
    """
    cameras = get_cameras(config)
    streams = get_go2rtc_streams(config)
    cam_names = sorted(cameras.keys(), key=len, reverse=True)
    result = {name: [] for name in cameras}
    for sname in streams:
        for cname in cam_names:
            if sname == cname or sname.startswith(cname + "_"):
                result[cname].append(sname)
                break
    return result


def add_camera(config: dict[str, Any], name: str, camera_data: dict[str, Any],
               streams: dict[str, list[str]] | None = None,
               stream_roles: dict[str, str] | None = None) -> None:
    """Add a camera and its associated go2rtc streams."""
    if "cameras" not in config:
        config["cameras"] = {}
    config["cameras"][name] = camera_data

    if streams:
        if "go2rtc" not in config:
            config["go2rtc"] = {}
        if "streams" not in config["go2rtc"]:
            config["go2rtc"]["streams"] = {}
        config["go2rtc"]["streams"].update(streams)

    # Auto-generate ffmpeg inputs from go2rtc streams if not provided
    if not camera_data.get("ffmpeg", {}).get("inputs") and streams:
        inputs = []
        for stream_name, _ in streams.items():
            if stream_roles and stream_name in stream_roles:
                roles = [stream_roles[stream_name]]
            else:
                roles = ["detect"] if "_sub" in stream_name else ["record"]
            inputs.append({
                "path": f"rtsp://127.0.0.1:8554/{stream_name}",
                "input_args": "preset-rtsp-restream",
                "roles": roles,
            })
        if "ffmpeg" not in camera_data:
            camera_data["ffmpeg"] = {}
        camera_data["ffmpeg"]["inputs"] = inputs


def rename_camera(config: dict[str, Any], old_name: str, new_name: str) -> None:
    """Rename a camera and update all associated go2rtc streams and references."""
    cameras = config.get("cameras", {})
    if old_name not in cameras:
        return

    camera = cameras.pop(old_name)
    cameras[new_name] = camera

    # Rename go2rtc streams
    streams = config.get("go2rtc", {}).get("streams", {})
    renames = {}
    for stream_name in list(streams.keys()):
        if stream_name == old_name or stream_name.startswith(f"{old_name}_"):
            new_stream_name = stream_name.replace(old_name, new_name, 1)
            streams[new_stream_name] = streams.pop(stream_name)
            renames[stream_name] = new_stream_name

    # Update ffmpeg input paths
    for inp in camera.get("ffmpeg", {}).get("inputs", []):
        path = inp.get("path", "")
        for old_stream, new_stream in renames.items():
            if f"127.0.0.1:8554/{old_stream}" in path:
                inp["path"] = path.replace(f"127.0.0.1:8554/{old_stream}", f"127.0.0.1:8554/{new_stream}")

    # Update camera_groups references
    for group in config.get("camera_groups", {}).values():
        if "cameras" in group:
            group["cameras"] = [new_name if c == old_name else c for c in group["cameras"]]


def delete_camera(config: dict[str, Any], name: str) -> None:
    """Delete a camera and its associated go2rtc streams."""
    cameras = config.get("cameras", {})
    camera = cameras.get(name)

    if name in cameras:
        del cameras[name]

    # Delete associated go2rtc streams
    streams = config.get("go2rtc", {}).get("streams", {})

    # Collect stream names to delete:
    # 1. Streams matching camera name or starting with {name}_
    # 2. Streams referenced in this camera's ffmpeg inputs
    streams_to_delete = set()
    for stream_name in list(streams.keys()):
        if stream_name == name or stream_name.startswith(f"{name}_"):
            streams_to_delete.add(stream_name)

    if camera:
        for inp in camera.get("ffmpeg", {}).get("inputs", []):
            path = inp.get("path", "")
            if "127.0.0.1:8554/" in path:
                stream_name = path.split("127.0.0.1:8554/")[1].split("?")[0]
                streams_to_delete.add(stream_name)

    # Only delete a stream if no other camera references it
    other_cameras = {k: v for k, v in cameras.items() if k != name}
    for stream_name in streams_to_delete:
        # Check if any other camera uses this stream
        in_use = False
        for other_cam in other_cameras.values():
            for inp in other_cam.get("ffmpeg", {}).get("inputs", []):
                path = inp.get("path", "")
                if f"127.0.0.1:8554/{stream_name}" in path:
                    in_use = True
                    break
            if in_use:
                break
        if not in_use and stream_name in streams:
            del streams[stream_name]

    # Remove from camera_groups
    for group in config.get("camera_groups", {}).values():
        if "cameras" in group:
            group["cameras"] = [c for c in group["cameras"] if c != name]


def update_camera_streams(config: dict[str, Any], camera_name: str,
                          new_streams: dict[str, list[str]],
                          stream_roles: dict[str, str] | None = None) -> None:
    """Update go2rtc streams for a camera, syncing ffmpeg inputs."""
    camera = get_camera(config, camera_name)
    if not camera:
        return

    old_streams = get_camera_streams(config, camera_name)
    all_streams = config.get("go2rtc", {}).get("streams", {})

    # Remove old streams associated with this camera
    for stream_name in old_streams:
        if stream_name in all_streams:
            del all_streams[stream_name]

    # Add new streams
    all_streams.update(new_streams)

    # Rebuild ffmpeg inputs from new streams
    inputs = []
    for stream_name, _ in new_streams.items():
        if stream_roles and stream_name in stream_roles:
            roles = [stream_roles[stream_name]]
        else:
            roles = ["detect"] if "_sub" in stream_name else ["record"]
        inputs.append({
            "path": f"rtsp://127.0.0.1:8554/{stream_name}",
            "input_args": "preset-rtsp-restream",
            "roles": roles,
        })

    if "ffmpeg" not in camera:
        camera["ffmpeg"] = {}
    camera["ffmpeg"]["inputs"] = inputs


def reorder_cameras(config: dict[str, Any], order: list[str]) -> None:
    """Reorder cameras in the config."""
    cameras = config.get("cameras", {})
    new_cameras = {}
    for name in order:
        if name in cameras:
            new_cameras[name] = cameras[name]
    # Add any cameras not in the order list
    for name, data in cameras.items():
        if name not in new_cameras:
            new_cameras[name] = data
    config["cameras"] = new_cameras


def deep_get(d: dict[str, Any], path: str) -> Any:
    """Get nested value by dot-separated path."""
    keys = path.split(".")
    val = d
    for k in keys:
        if isinstance(val, dict):
            val = val.get(k)
        else:
            return None
    return val


def deep_set(d: dict[str, Any], path: str, value: Any) -> None:
    """Set nested value by dot-separated path."""
    keys = path.split(".")
    for k in keys[:-1]:
        if k not in d or not isinstance(d[k], dict):
            d[k] = {}
        d = d[k]
    if value is None or (isinstance(value, (dict, list)) and not value):
        d.pop(keys[-1], None)
    else:
        d[keys[-1]] = value


def deep_clone(obj: Any) -> Any:
    return copy.deepcopy(obj)


def update_stream_credentials(stream_urls: list[str], username: str, password: str) -> list[str]:
    """Replace credentials in RTSP stream URLs with URL-encoded username/password."""
    safe_user = quote(username, safe="")
    safe_pass = quote(password, safe="")
    updated = []
    for url in stream_urls:
        if "rtsp://" in url:
            rest = url.split("rtsp://", 1)[1]
            if "@" in rest:
                rest = rest.split("@", 1)[1]
            updated.append(f"rtsp://{safe_user}:{safe_pass}@{rest}")
        else:
            updated.append(url)
    return updated


def apply_credentials_to_camera_streams(config: dict[str, Any], camera_name: str,
                                        username: str, password: str) -> list[str]:
    """Apply credentials to all go2rtc streams associated with a camera.

    Returns list of updated stream names.
    """
    camera_streams = get_camera_streams(config, camera_name)
    all_streams = config.get("go2rtc", {}).get("streams", {})
    updated = []
    for stream_name, urls in camera_streams.items():
        if stream_name in all_streams:
            all_streams[stream_name] = update_stream_credentials(urls, username, password)
            updated.append(stream_name)
    return updated
