"""Frigate configuration schema definitions.

Describes all config sections, fields, types, defaults, and descriptions.
Drives UI generation and config validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class FieldType(Enum):
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    ENUM = "enum"
    LIST = "list"
    DICT = "dict"
    PATH = "path"
    PASSWORD = "password"
    TEXT = "text"  # multi-line string
    SECTION = "section"  # nested group of fields


@dataclass
class ConfigField:
    name: str
    label: str
    type: FieldType
    default: Any = None
    description: str = ""
    required: bool = False
    options: list[str] = field(default_factory=list)
    # For LIST type: item schema (field name template or sub-fields)
    item_fields: list[ConfigField] = field(default_factory=list)
    # For DICT/SECTION type: nested fields
    fields: list[ConfigField] = field(default_factory=list)
    # For DICT type: whether keys are user-defined (like camera names)
    dict_key_label: str = ""
    # Whether this field can be overridden at camera level
    camera_overridable: bool = False
    # Whether to show this field in the UI (some are advanced)
    advanced: bool = False
    # Placeholder text
    placeholder: str = ""
    # Source for list options (e.g. "cameras" → populated from config camera names)
    options_source: str = ""


@dataclass
class ConfigSection:
    name: str
    label: str
    description: str
    required: bool = False
    camera_overridable: bool = False
    fields: list[ConfigField] = field(default_factory=list)
    # For dict-type sections (like cameras, detectors) where keys are user-defined names
    is_dict_collection: bool = False
    # Label for the key input in dict collections (e.g. "Detector Name")
    dict_key_label: str = ""
    # Template fields for dict collection items
    item_fields: list[ConfigField] = field(default_factory=list)


# --- Field helpers ---

def f_str(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.STRING, default=default, **kw)

def f_int(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.INTEGER, default=default, **kw)

def f_float(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.FLOAT, default=default, **kw)

def f_bool(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.BOOLEAN, default=default, **kw)

def f_enum(name, label, options, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.ENUM, default=default, options=options, **kw)

def f_list(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.LIST, default=default or [], **kw)

def f_path(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.PATH, default=default, **kw)

def f_pwd(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.PASSWORD, default=default, **kw)

def f_text(name, label, default=None, **kw):
    return ConfigField(name=name, label=label, type=FieldType.TEXT, default=default, **kw)

def f_section(name, label, fields, **kw):
    return ConfigField(name=name, label=label, type=FieldType.SECTION, fields=fields, **kw)

def f_dict(name, label, fields=None, dict_key_label="", **kw):
    return ConfigField(name=name, label=label, type=FieldType.DICT, fields=fields or [], dict_key_label=dict_key_label, **kw)


# --- Section definitions ---

MQTT = ConfigSection(
    name="mqtt", label="MQTT", description="MQTT server configuration for Frigate.",
    fields=[
        f_bool("enabled", "Enabled", True, description="Enable MQTT server."),
        f_str("host", "Host", "mqtt.server.com", required=True, description="MQTT server hostname. Can use env vars like {FRIGATE_MQTT_HOST}."),
        f_int("port", "Port", 1883, description="MQTT server port."),
        f_str("topic_prefix", "Topic Prefix", "frigate", description="Topic prefix. Must be unique for multiple instances."),
        f_str("client_id", "Client ID", "frigate", description="Client ID. Must be unique for multiple instances."),
        f_str("user", "User", description="MQTT username. Can use env vars."),
        f_pwd("password", "Password", description="MQTT password. Can use env vars."),
        f_path("tls_ca_certs", "TLS CA Certs", description="Path to CA cert for self-signed TLS."),
        f_path("tls_client_cert", "TLS Client Cert", description="Path to client cert."),
        f_path("tls_client_key", "TLS Client Key", description="Path to client key."),
        f_bool("tls_insecure", "TLS Insecure", False, description="Skip TLS hostname verification."),
        f_int("stats_interval", "Stats Interval (s)", 60, description="Interval for publishing stats."),
        f_int("qos", "QoS Level", 0, description="QoS level: 0=at most once, 1=at least once, 2=exactly once."),
    ],
)

DETECTORS = ConfigSection(
    name="detectors", label="Detectors", description="Object detector configuration. Defaults to a single CPU detector.",
    is_dict_collection=True,
    dict_key_label="Detector Name",
    item_fields=[
        f_enum("type", "Type", ["cpu", "edgetpu", "openvino", "rocm", "tensorrt"], "cpu", required=True,
               description="Detector type. See docs for details."),
        f_str("device", "Device", description="Device path (e.g. 'usb' for EdgeTPU, 'pci' for PCIe EdgeTPU)."),
        f_int("num_threads", "Num Threads", description="Number of detection threads (CPU only)."),
    ],
)

DATABASE = ConfigSection(
    name="database", label="Database", description="SQLite database configuration.",
    fields=[
        f_path("path", "Path", "/config/frigate.db", description="Path to store the SQLite DB."),
    ],
)

TLS = ConfigSection(
    name="tls", label="TLS", description="TLS configuration for port 8971.",
    fields=[
        f_bool("enabled", "Enabled", True, description="Enable TLS for port 8971."),
    ],
)

NETWORKING = ConfigSection(
    name="networking", label="Networking", description="IPv6 configuration.",
    fields=[
        f_section("ipv6", "IPv6", [
            f_bool("enabled", "Enabled", False, description="Enable IPv6 on ports 5000 and 8971."),
        ]),
    ],
)

PROXY = ConfigSection(
    name="proxy", label="Proxy", description="Proxy configuration for upstream auth.",
    fields=[
        f_dict("header_map", "Header Map", [
            f_str("user", "User Header", "x-forwarded-user"),
            f_str("role", "Role Header", "x-forwarded-groups"),
        ], advanced=True),
        f_str("logout_url", "Logout URL", description="URL for logging out a user."),
        f_str("auth_secret", "Auth Secret", description="Secret checked against X-Proxy-Secret header."),
        f_enum("default_role", "Default Role", ["admin", "viewer"], "viewer"),
        f_str("separator", "Separator", ",", description="Character for separating multiple values in proxy headers."),
    ],
)

AUTH = ConfigSection(
    name="auth", label="Authentication", description="Authentication configuration.",
    fields=[
        f_bool("enabled", "Enabled", True, description="Enable authentication."),
        f_bool("reset_admin_password", "Reset Admin Password", False, description="Reset admin password on startup."),
        f_str("cookie_name", "Cookie Name", "frigate_token"),
        f_bool("cookie_secure", "Cookie Secure", False, description="Set secure flag on cookie. Use True with TLS."),
        f_int("session_length", "Session Length (s)", 86400, description="Session length in seconds."),
        f_int("refresh_time", "Refresh Time (s)", 1800, description="Refresh time before expiry."),
        f_str("failed_login_rate_limit", "Failed Login Rate Limit", description="Rate limiting for brute force prevention."),
        f_list("trusted_proxies", "Trusted Proxies", default=[], description="Trusted proxies for rate limiting."),
        f_int("hash_iterations", "Hash Iterations", 600000, description="PBKDF2-SHA256 iterations.", advanced=True),
    ],
)

MODEL = ConfigSection(
    name="model", label="Model", description="Object detection model configuration.",
    fields=[
        f_path("path", "Model Path", "/edgetpu_model.tflite", description="Path to model file. Frigate+ models use plus://<model_id>."),
        f_path("labelmap_path", "Labelmap Path", "/labelmap.txt"),
        f_int("width", "Input Width", 320),
        f_int("height", "Input Height", 320),
        f_enum("input_pixel_format", "Input Pixel Format", ["rgb", "bgr", "yuv"], "rgb"),
        f_enum("input_tensor", "Input Tensor", ["nhwc", "nchw"], "nhwc"),
        f_enum("model_type", "Model Type", ["ssd", "yolox", "yolonas"], "ssd", description="Used with OpenVINO detector."),
        f_dict("labelmap", "Labelmap", dict_key_label="Label ID", description="Label name modifications."),
        f_dict("attributes_map", "Attributes Map", dict_key_label="Object Label", description="Map of object labels to attribute labels.", advanced=True),
    ],
)

AUDIO = ConfigSection(
    name="audio", label="Audio", description="Audio events configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False),
        f_int("max_not_heard", "Max Not Heard (s)", 30, description="Seconds without audio to end event."),
        f_int("min_volume", "Min Volume", 500, description="Min RMS volume. 200=high, 500=medium, 1000=low sensitivity."),
        f_list("listen", "Listen For", default=["bark", "fire_alarm", "scream", "speech", "yell"], description="Types of audio to listen for."),
        f_dict("filters", "Filters", dict_key_label="Audio Label", advanced=True),
    ],
)

LOGGER = ConfigSection(
    name="logger", label="Logger", description="Logger verbosity settings.",
    fields=[
        f_enum("default", "Default Level", ["debug", "info", "warning", "error", "critical"], "info"),
        f_dict("logs", "Component Logs", dict_key_label="Component", description="Component-specific logger overrides.", advanced=True),
    ],
)

ENVIRONMENT_VARS = ConfigSection(
    name="environment_vars", label="Environment Variables", description="Set environment variables.",
    is_dict_collection=True,
    item_fields=[
        f_str("value", "Value", description="Value for the variable."),
    ],
)

BIRDSYE = ConfigSection(
    name="birdseye", label="Birdseye", description="Birdseye view configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", True),
        f_bool("restream", "Restream", False, description="Restream birdseye via RTSP. Increases CPU usage."),
        f_int("width", "Width", 1280),
        f_int("height", "Height", 720),
        f_int("quality", "Quality", 8, description="Encoding quality 1-31. Lower=less CPU."),
        f_enum("mode", "Mode", ["objects", "motion", "continuous"], "objects"),
        f_int("inactivity_threshold", "Inactivity Threshold (s)", 30),
        f_section("layout", "Layout", [
            f_float("scaling_factor", "Scaling Factor", 2.0, description="Layout calculator scaling 1.0-5.0."),
            f_int("max_cameras", "Max Cameras", description="Max cameras to show at once."),
        ]),
        f_float("idle_heartbeat_fps", "Idle Heartbeat FPS", 0.0, advanced=True),
    ],
)

FFMPEG = ConfigSection(
    name="ffmpeg", label="FFmpeg", description="Global ffmpeg configuration.",
    fields=[
        f_str("path", "Path", "default", description="ffmpeg binary path or version '7.0'/'5.0'."),
        f_str("global_args", "Global Args", "-hide_banner -loglevel warning -threads 2"),
        f_str("hwaccel_args", "HWAccel Args", "auto", description="Hardware acceleration args. See docs."),
        f_str("input_args", "Input Args", "preset-rtsp-generic"),
        f_section("output_args", "Output Args", [
            f_str("detect", "Detect Args", "-threads 2 -f rawvideo -pix_fmt yuv420p"),
            f_str("record", "Record Args", "preset-record-generic"),
        ]),
        f_int("retry_interval", "Retry Interval (s)", 10, description="Seconds before ffmpeg retries connection."),
        f_bool("apple_compatibility", "Apple Compatibility", False, description="HEVC tag for Apple players."),
        f_int("gpu", "GPU Index", 0, description="GPU index for hardware acceleration."),
    ],
)

DETECT = ConfigSection(
    name="detect", label="Detect", description="Detection configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False),
        f_int("width", "Width", 1280, description="Frame width for detect stream."),
        f_int("height", "Height", 720, description="Frame height for detect stream."),
        f_int("fps", "FPS", 5, description="Desired FPS. Recommended 5."),
        f_int("min_initialized", "Min Initialized", 2, description="Consecutive hits to initialize tracker."),
        f_int("max_disappeared", "Max Disappeared", 25, description="Frames without detection before object gone."),
        f_section("stationary", "Stationary", [
            f_bool("classifier", "Classifier", True, description="Visual characteristics to determine stationary."),
            f_int("interval", "Interval", 50, description="Frequency for confirming stationary objects."),
            f_int("threshold", "Threshold", 50, description="Frames without position change for stationary."),
            f_section("max_frames", "Max Frames", [
                f_int("default", "Default", description="Default max frames for all objects."),
                f_dict("objects", "Object Specific", dict_key_label="Object", advanced=True),
            ], advanced=True),
        ]),
        f_int("annotation_offset", "Annotation Offset (ms)", 0, description="Milliseconds to offset detect annotations."),
    ],
)

OBJECTS = ConfigSection(
    name="objects", label="Objects", description="Object tracking configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_list("track", "Track", default=["person"], description="Objects to track from labelmap."),
        f_str("mask", "Mask", description="Mask to prevent detection in areas. Bottom center of bounding box."),
        f_dict("filters", "Filters", [
            f_int("min_area", "Min Area", 0, description="Min bounding box size. Integer or decimal percentage."),
            f_int("max_area", "Max Area", 24000000),
            f_float("min_ratio", "Min Ratio", 0),
            f_float("max_ratio", "Max Ratio", 24000000),
            f_float("min_score", "Min Score", 0.5, description="Min score to initiate tracking."),
            f_float("threshold", "Threshold", 0.7, description="Min computed score for true positive."),
            f_str("mask", "Mask", description="Object-specific mask."),
        ], dict_key_label="Object Label", advanced=True),
        f_section("genai", "GenAI Descriptions", [
            f_bool("enabled", "Enabled", False),
            f_bool("use_snapshot", "Use Snapshot", False),
            f_text("prompt", "Prompt", "Describe the {label} in the sequence of images with as much detail as possible. Do not describe the background."),
            f_dict("object_prompts", "Object Prompts", dict_key_label="Object"),
            f_list("objects", "Objects", description="Objects to generate descriptions for."),
            f_list("required_zones", "Required Zones", default=[]),
            f_section("send_triggers", "Send Triggers", [
                f_bool("tracked_object_end", "Tracked Object End", True),
                f_int("after_significant_updates", "After Significant Updates", description="Send after N significant updates."),
            ]),
            f_bool("debug_save_thumbnails", "Debug Save Thumbnails", False, advanced=True),
        ], advanced=True),
    ],
)

REVIEW = ConfigSection(
    name="review", label="Review", description="Review configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_section("alerts", "Alerts", [
            f_bool("enabled", "Enabled", True),
            f_list("labels", "Labels", default=["car", "person"]),
            f_int("cutoff_time", "Cutoff Time (s)", 40),
            f_list("required_zones", "Required Zones", default=[]),
        ]),
        f_section("detections", "Detections", [
            f_bool("enabled", "Enabled", True),
            f_list("labels", "Labels", default=["car", "person"]),
            f_int("cutoff_time", "Cutoff Time (s)", 30),
            f_list("required_zones", "Required Zones", default=[]),
        ]),
        f_section("genai", "GenAI Review", [
            f_bool("enabled", "Enabled", False),
            f_bool("alerts", "Alerts", True),
            f_bool("detections", "Detections", False),
            f_text("activity_context_prompt", "Activity Context Prompt", 'Define what is and is not suspicious'),
            f_enum("image_source", "Image Source", ["preview", "recordings"], "preview"),
            f_list("additional_concerns", "Additional Concerns"),
            f_str("preferred_language", "Preferred Language", "English"),
        ], advanced=True),
    ],
)

MOTION = ConfigSection(
    name="motion", label="Motion", description="Motion configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False, description="Required for object detection."),
        f_int("threshold", "Threshold", 30, description="Pixel difference threshold 1-255."),
        f_float("lightning_threshold", "Lightning Threshold", 0.8),
        f_int("contour_area", "Contour Area", 10, description="Min motion size. 10=high, 30=medium, 50=low sensitivity."),
        f_float("frame_alpha", "Frame Alpha", 0.01, description="Background averaging alpha."),
        f_int("frame_height", "Frame Height", 100, description="Height of resized motion frame."),
        f_str("mask", "Mask", description="Motion mask."),
        f_bool("improve_contrast", "Improve Contrast", True),
        f_int("mqtt_off_delay", "MQTT Off Delay (s)", 30),
    ],
)

NOTIFICATIONS = ConfigSection(
    name="notifications", label="Notifications", description="Notification configuration. Can be overridden at camera level (except email).",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False),
        f_str("email", "Email", description="Email for push service. Required for notifications."),
        f_int("cooldown", "Cooldown (s)", 0, description="Cooldown between notifications."),
    ],
)

RECORD = ConfigSection(
    name="record", label="Record", description="Recording configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False, description="Enable recording. Cannot be enabled via UI if disabled in config."),
        f_int("expire_interval", "Expire Interval (min)", 60, description="Minutes between cleanup runs."),
        f_bool("sync_recordings", "Sync Recordings", False),
        f_section("continuous", "Continuous", [
            f_int("days", "Days", 0, description="Days to retain all recordings."),
        ]),
        f_section("motion", "Motion", [
            f_int("days", "Days", 0, description="Days to retain motion recordings."),
        ]),
        f_section("export", "Export", [
            f_str("timelapse_args", "Timelapse Args", "-vf setpts=0.04*PTS -r 30", advanced=True),
        ], advanced=True),
        f_section("preview", "Preview", [
            f_enum("quality", "Quality", ["very_low", "low", "medium", "high", "very_high"], "medium"),
        ]),
        f_section("alerts", "Alert Recordings", [
            f_int("pre_capture", "Pre Capture (s)", 5),
            f_int("post_capture", "Post Capture (s)", 5),
            f_section("retain", "Retention", [
                f_int("days", "Days", 10),
                f_enum("mode", "Mode", ["all", "motion", "active_objects"], "motion"),
            ]),
        ]),
        f_section("detections", "Detection Recordings", [
            f_int("pre_capture", "Pre Capture (s)", 5),
            f_int("post_capture", "Post Capture (s)", 5),
            f_section("retain", "Retention", [
                f_int("days", "Days", 10),
                f_enum("mode", "Mode", ["all", "motion", "active_objects"], "motion"),
            ]),
        ]),
    ],
)

SNAPSHOTS = ConfigSection(
    name="snapshots", label="Snapshots", description="JPG snapshot configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False),
        f_bool("clean_copy", "Clean Copy", True),
        f_bool("timestamp", "Timestamp", False),
        f_bool("bounding_box", "Bounding Box", True),
        f_bool("crop", "Crop", False),
        f_int("height", "Height", 175),
        f_list("required_zones", "Required Zones", default=[]),
        f_section("retain", "Retention", [
            f_int("default", "Default Days", 10),
            f_dict("objects", "Per Object", dict_key_label="Object"),
        ]),
        f_int("quality", "Quality", 70, description="JPEG quality 0-100."),
    ],
)

SEMANTIC_SEARCH = ConfigSection(
    name="semantic_search", label="Semantic Search", description="Semantic search configuration.",
    fields=[
        f_bool("enabled", "Enabled", False),
        f_bool("reindex", "Reindex", False),
        f_str("model", "Model", "jinav1"),
        f_enum("model_size", "Model Size", ["small", "large"], "small", description="Small=CPU, Large=GPU."),
        f_str("device", "Device", description="Target device for model."),
    ],
)

FACE_RECOGNITION = ConfigSection(
    name="face_recognition", label="Face Recognition", description="Face recognition configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False),
        f_float("unknown_score", "Unknown Score", 0.8),
        f_float("detection_threshold", "Detection Threshold", 0.7),
        f_float("recognition_threshold", "Recognition Threshold", 0.9),
        f_int("min_area", "Min Area", 500, camera_overridable=True),
        f_int("min_faces", "Min Faces", 1),
        f_int("save_attempts", "Save Attempts", 200),
        f_bool("blur_confidence_filter", "Blur Confidence Filter", True),
        f_enum("model_size", "Model Size", ["small", "large"], "small"),
        f_str("device", "Device", description="Target device."),
    ],
)

LPR = ConfigSection(
    name="lpr", label="License Plate Recognition", description="LPR configuration. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_bool("enabled", "Enabled", False),
        f_str("device", "Device", "CPU"),
        f_enum("model_size", "Model Size", ["small", "large"], "small"),
        f_float("detection_threshold", "Detection Threshold", 0.7),
        f_int("min_area", "Min Area", 1000, camera_overridable=True),
        f_float("recognition_threshold", "Recognition Threshold", 0.9),
        f_int("min_plate_length", "Min Plate Length", 4),
        f_str("format", "Format", description="Regex for expected plate format."),
        f_int("match_distance", "Match Distance", 1, description="Allowed missing/incorrect characters."),
        f_dict("known_plates", "Known Plates", dict_key_label="Plate Name"),
        f_int("enhancement", "Enhancement", 0, description="Contrast/denoise 0-10.", camera_overridable=True),
        f_bool("debug_save_plates", "Debug Save Plates", False, advanced=True),
    ],
)

GENAI = ConfigSection(
    name="genai", label="GenAI Provider", description="AI/LLM provider configuration.",
    fields=[
        f_enum("provider", "Provider", ["ollama", "gemini", "openai"], "ollama", required=True),
        f_str("base_url", "Base URL", description="Required for ollama. Or OpenAI-compatible backend."),
        f_pwd("api_key", "API Key", description="Required for gemini or openai. Can use env vars."),
        f_str("model", "Model", "gemini-1.5-flash", required=True),
        f_dict("provider_options", "Provider Options", dict_key_label="Option", advanced=True),
        f_dict("runtime_options", "Runtime Options", dict_key_label="Option", advanced=True),
    ],
)

AUDIO_TRANSCRIPTION = ConfigSection(
    name="audio_transcription", label="Audio Transcription", description="Audio transcription configuration.",
    fields=[
        f_bool("enabled", "Enabled", False),
        f_str("device", "Device", "CPU"),
        f_enum("model_size", "Model Size", ["small", "large"], "small"),
        f_str("language", "Language", "en", description="Language code for transcription."),
    ],
)

CLASSIFICATION = ConfigSection(
    name="classification", label="Classification", description="Classification models configuration.",
    fields=[
        f_section("bird", "Bird Classification", [
            f_bool("enabled", "Enabled", False),
            f_float("threshold", "Threshold", 0.9),
        ]),
        f_dict("custom", "Custom Classification", dict_key_label="Model Name", advanced=True),
    ],
)

GO2RTC = ConfigSection(
    name="go2rtc", label="Go2RTC / Restream", description="Restream configuration using go2rtc. Streams are managed per-camera.",
    fields=[
        f_dict("streams", "Streams", dict_key_label="Stream Name", description="go2rtc stream definitions. Managed per-camera."),
        f_dict("ffmpeg", "FFmpeg", dict_key_label="Codec", advanced=True),
    ],
)

LIVE = ConfigSection(
    name="live", label="Live View", description="Live stream configuration for WebUI. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_dict("streams", "Streams", dict_key_label="Stream Label", description="Friendly name → go2rtc stream name for live view in WebUI. Usually set at camera level only."),
        f_int("height", "Height", 720, description="jsmpeg stream height. Must be <= detect height."),
        f_int("quality", "Quality", 8, description="jsmpeg encode quality 1-31."),
    ],
)

TIMESTAMP_STYLE = ConfigSection(
    name="timestamp_style", label="Timestamp Style", description="In-feed timestamp style. Can be overridden at camera level.",
    camera_overridable=True,
    fields=[
        f_enum("position", "Position", ["tl", "tr", "bl", "br"], "tl", description="tl=top left, tr=top right, bl=bottom left, br=bottom right"),
        f_str("format", "Format", "%m/%d/%Y %H:%M:%S", description="Python datetime format."),
        f_section("color", "Color", [
            f_int("red", "Red", 255),
            f_int("green", "Green", 255),
            f_int("blue", "Blue", 255),
        ]),
        f_int("thickness", "Thickness", 2),
        f_enum("effect", "Effect", ["None", "solid", "shadow"], "None"),
    ],
)

UI_CONFIG = ConfigSection(
    name="ui", label="UI Settings", description="Frigate UI configuration.",
    fields=[
        f_str("timezone", "Timezone", description="e.g. America/Denver. Defaults to browser local time."),
        f_enum("time_format", "Time Format", ["browser", "12hour", "24hour"], "browser"),
        f_enum("date_style", "Date Style", ["full", "long", "medium", "short"], "short"),
        f_enum("time_style", "Time Style", ["full", "long", "medium", "short"], "medium"),
        f_enum("unit_system", "Unit System", ["metric", "imperial"], "metric"),
    ],
)

TELEMETRY = ConfigSection(
    name="telemetry", label="Telemetry", description="Telemetry configuration.",
    fields=[
        f_list("network_interfaces", "Network Interfaces", default=["eth", "enp", "eno", "ens", "wl", "lo"]),
        f_section("stats", "Stats", [
            f_bool("amd_gpu_stats", "AMD GPU Stats", True),
            f_bool("intel_gpu_stats", "Intel GPU Stats", True),
            f_str("intel_gpu_device", "Intel GPU Device", description="Treat GPU as SR-IOV."),
            f_bool("network_bandwidth", "Network Bandwidth", False),
        ]),
        f_bool("version_check", "Version Check", True),
    ],
)

CAMERA_GROUPS = ConfigSection(
    name="camera_groups", label="Camera Groups", description="Camera groups for UI organization.",
    is_dict_collection=True,
    item_fields=[
        f_list("cameras", "Cameras", required=True, description="List of camera names in this group.", options_source="cameras"),
        f_str("icon", "Icon", required=True, description="Lucide icon name (e.g. LuCar)."),
        f_int("order", "Order", 0),
    ],
)

# --- Camera-specific fields (for camera editor) ---

CAMERA_FIELDS = [
    f_bool("enabled", "Enabled", True, description="Enable/disable camera."),
    f_enum("type", "Type", ["generic", "lpr"], "generic", description="Camera type for Frigate features."),
    f_section("ffmpeg", "FFmpeg", [
        f_list("inputs", "Inputs", description="Input streams for the camera.", item_fields=[
            f_str("path", "Path", required=True, description="Stream path. Usually rtsp://127.0.0.1:8554/{stream_name}"),
            f_list("roles", "Roles", description="Valid: audio, detect, record"),
            f_str("input_args", "Input Args", description="Override global input args."),
            f_str("hwaccel_args", "HWAccel Args", description="Override global hwaccel args."),
            f_str("global_args", "Global Args", description="Override global args."),
        ]),
        f_str("global_args", "Global Args", description="Camera-specific global args."),
        f_str("hwaccel_args", "HWAccel Args", description="Camera-specific hwaccel args."),
        f_str("input_args", "Input Args", description="Camera-specific input args."),
        f_section("output_args", "Output Args", [
            f_str("detect", "Detect", description="Override detect output args."),
            f_str("record", "Record", description="Override record output args."),
        ]),
    ]),
    f_int("best_image_timeout", "Best Image Timeout (s)", 60, description="Timeout for highest scoring image."),
    f_str("webui_url", "WebUI URL", description="URL to camera web UI."),
    f_section("zones", "Zones", [], description="Zones for this camera."),
    f_section("mqtt", "MQTT Snapshots", [
        f_bool("enabled", "Enabled", True),
        f_bool("timestamp", "Timestamp", True),
        f_bool("bounding_box", "Bounding Box", True),
        f_bool("crop", "Crop", True),
        f_int("height", "Height", 270),
        f_int("quality", "Quality", 70),
        f_list("required_zones", "Required Zones", default=[]),
    ]),
    f_section("ui", "UI", [
        f_int("order", "Order", 0, description="Sort order. Larger = later."),
        f_bool("dashboard", "Dashboard", True, description="Show in Frigate UI."),
    ]),
    f_section("onvif", "ONVIF / PTZ", [
        f_str("host", "Host", description="Camera host for ONVIF."),
        f_int("port", "Port", 8000),
        f_str("user", "User", "admin"),
        f_pwd("password", "Password", "admin"),
        f_bool("tls_insecure", "TLS Insecure", False),
        f_bool("ignore_time_mismatch", "Ignore Time Mismatch", False),
        f_section("autotracking", "Autotracking", [
            f_bool("enabled", "Enabled", False),
            f_bool("calibrate_on_startup", "Calibrate on Startup", False),
            f_enum("zooming", "Zooming", ["disabled", "absolute", "relative"], "disabled"),
            f_float("zoom_factor", "Zoom Factor", 0.3, description="0.1-0.75. Higher = more zoom."),
            f_list("track", "Track", default=["person"]),
            f_list("required_zones", "Required Zones", required=True),
            f_str("return_preset", "Return Preset", "home", required=True),
            f_int("timeout", "Timeout (s)", 10),
            f_list("movement_weights", "Movement Weights", default=[], advanced=True),
        ]),
    ]),
    f_section("birdseye", "Birdseye", [
        f_int("order", "Order", 0),
    ]),
    f_section("triggers", "Triggers", [], description="Semantic search triggers.", advanced=True),
]

# Camera-level overrides for global sections
CAMERA_OVERRIDE_SECTIONS = [
    "detect", "objects", "motion", "record", "snapshots", "audio",
    "birdseye", "live", "timestamp_style", "review", "notifications",
    "face_recognition", "lpr",
]

# --- All sections in order ---

ALL_SECTIONS: list[ConfigSection] = [
    MQTT, DETECTORS, DATABASE, TLS, NETWORKING, PROXY, AUTH, MODEL,
    AUDIO, LOGGER, ENVIRONMENT_VARS, BIRDSYE, FFMPEG, DETECT, OBJECTS,
    REVIEW, MOTION, NOTIFICATIONS, RECORD, SNAPSHOTS, SEMANTIC_SEARCH,
    FACE_RECOGNITION, LPR, GENAI, AUDIO_TRANSCRIPTION, CLASSIFICATION,
    GO2RTC, LIVE, TIMESTAMP_STYLE, UI_CONFIG, TELEMETRY, CAMERA_GROUPS,
]

SECTION_MAP: dict[str, ConfigSection] = {s.name: s for s in ALL_SECTIONS}

# Sections that appear in the sidebar grouped
SECTION_GROUPS = {
    "Global": ["mqtt", "detectors", "database", "tls", "networking", "proxy", "auth", "model", "logger", "environment_vars", "ui", "telemetry"],
    "Detection": ["ffmpeg", "detect", "objects", "motion", "review", "notifications"],
    "Recording": ["record", "snapshots", "birdseye"],
    "AI Features": ["genai", "audio", "audio_transcription", "classification", "semantic_search", "face_recognition", "lpr"],
    "Streaming": ["go2rtc", "live", "timestamp_style"],
    "Cameras": ["cameras", "camera_groups"],
}
