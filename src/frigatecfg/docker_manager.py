"""Docker manager: restart frigate container, test camera connections."""

from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
from typing import Any


def get_docker_host() -> str:
    return os.environ.get("FRIGATE_DOCKER_HOST", "unix:///var/run/docker.sock")


def get_frigate_container_name() -> str:
    return os.environ.get("FRIGATE_CONTAINER_NAME", "frigate")


class _UnixSocketHTTPConnection(http.client.HTTPConnection):
    """HTTP connection over a Unix domain socket (for Docker API)."""

    def __init__(self, socket_path: str, timeout: float = 60):
        super().__init__("localhost", timeout=timeout)
        self._socket_path = socket_path

    def connect(self):
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self._socket_path)


def _docker_conn(timeout: float = 60) -> http.client.HTTPConnection:
    """Create an HTTP connection to the Docker Engine API."""
    host = get_docker_host()
    if host.startswith("unix://"):
        path = host[len("unix://"):]
        return _UnixSocketHTTPConnection(path, timeout=timeout)
    # TCP host (e.g. tcp://192.168.1.100:2375)
    if host.startswith("tcp://"):
        addr = host[len("tcp://"):]
        h, _, p = addr.partition(":")
        return http.client.HTTPConnection(h, int(p or 2375), timeout=timeout)
    raise ValueError(f"Unsupported Docker host: {host}")


def _docker_request(method: str, path: str, timeout: float = 60) -> tuple[int, str]:
    """Make a request to the Docker Engine API. Returns (status_code, body)."""
    conn = _docker_conn(timeout=timeout)
    try:
        conn.request(method, path)
        resp = conn.getresponse()
        body = resp.read().decode("utf-8", errors="replace")
        return resp.status, body
    finally:
        conn.close()


def restart_frigate() -> dict[str, Any]:
    """Restart the frigate Docker container via Docker Engine API."""
    container = get_frigate_container_name()
    try:
        status, body = _docker_request("POST", f"/containers/{container}/restart", timeout=60)
        if status == 204:
            return {"success": True, "message": f"Container '{container}' restarted successfully."}
        else:
            msg = body[:300] if body else f"HTTP {status}"
            return {"success": False, "message": f"Failed to restart: {msg}"}
    except (FileNotFoundError, ConnectionRefusedError) as e:
        return {"success": False, "message": f"Cannot connect to Docker socket: {e}"}
    except socket.timeout:
        return {"success": False, "message": "Restart timed out after 60s."}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}


def get_frigate_status() -> dict[str, Any]:
    """Get frigate container status via Docker Engine API."""
    container = get_frigate_container_name()
    try:
        status, body = _docker_request("GET", f"/containers/{container}/json", timeout=10)
        if status == 200:
            info = json.loads(body)
            state = info.get("State", {})
            running = state.get("Running", False)
            return {"running": running, "status": state.get("Status", "unknown")}
        else:
            return {"running": False, "status": "not found"}
    except Exception:
        return {"running": False, "status": "error"}


def test_rtsp_connection(url: str, timeout: float = 10.0) -> dict[str, Any]:
    """Test RTSP connection by attempting actual stream probe with ffprobe.

    This verifies not just TCP connectivity but also:
    - RTSP handshake (DESCRIBE/SETUP)
    - Credential validity (auth challenge)
    - Stream accessibility (actual video/audio tracks)

    Falls back to TCP connect if ffprobe is not available.
    """
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
        host = parsed.hostname
        port = parsed.port or 554

        if not host:
            return {"success": False, "message": "Invalid URL: no host found."}
    except Exception as e:
        return {"success": False, "message": f"Error parsing URL: {e}"}

    # Try ffprobe first - actually verifies RTSP handshake + credentials
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "quiet",
                "-rtsp_transport", "tcp",
                "-timeout", str(int(timeout * 1000000)),
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                url,
            ],
            capture_output=True, text=True, timeout=timeout + 5,
        )

        if result.returncode == 0:
            import json
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
                details.append(f"Video: {codec} {w}x{h} @ {fps}fps")
            for _ in audio_streams:
                details.append("Audio: detected")

            detail_str = " | ".join(details) if details else "No tracks found"
            return {
                "success": True,
                "message": f"Stream verified on {host}:{port}. {detail_str}",
                "details": detail_str,
                "video": len(video_streams) > 0,
                "audio": len(audio_streams) > 0,
            }
        else:
            stderr = result.stderr.strip().lower()
            if "401" in stderr or "unauthorized" in stderr or "not authorized" in stderr:
                return {"success": False, "message": f"Authentication failed for {host}:{port}. Check credentials."}
            if "404" in stderr or "not found" in stderr:
                return {"success": False, "message": f"Stream path not found on {host}:{port}. Check URL path."}
            if "connection refused" in stderr:
                return {"success": False, "message": f"Connection refused by {host}:{port}."}
            if "timeout" in stderr or "timed out" in stderr:
                return {"success": False, "message": f"Connection to {host}:{port} timed out."}
            return {"success": False, "message": f"Stream test failed: {result.stderr.strip()[:200]}"}

    except subprocess.TimeoutExpired:
        return {"success": False, "message": f"Probe timed out after {timeout}s."}
    except FileNotFoundError:
        # ffprobe not installed - fall back to TCP connect
        pass
    except Exception as e:
        # ffprobe failed unexpectedly - fall back to TCP connect
        pass

    # Fallback: TCP connect only (less thorough)
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        try:
            sock.connect((host, port))
            sock.close()
            return {
                "success": True,
                "message": f"TCP connect to {host}:{port} succeeded (ffprobe unavailable - credentials not verified).",
                "warning": True,
            }
        except socket.timeout:
            return {"success": False, "message": f"Connection to {host}:{port} timed out."}
        except ConnectionRefusedError:
            return {"success": False, "message": f"Connection refused by {host}:{port}."}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {e}"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}
