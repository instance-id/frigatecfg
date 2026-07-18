"""Valid Frigate config schema: allowed keys at each level.

Built from the official Frigate reference config:
https://docs.frigate.video/configuration/advanced/reference

Each entry maps a config section to its allowed keys. Nested dicts
use the same structure recursively. A value of None means any key is
allowed (dict collections with user-defined keys). A value of True
means the key exists but has no sub-keys (leaf value).
"""

from __future__ import annotations

# Sentinel: any key allowed at this level
ANY_KEYS = None

# Camera-level allowed keys (from reference.md cameras section)
CAMERA_KEYS = {
    "enabled": True,
    "type": True,
    "ffmpeg": {
        "inputs": [  # list of dicts
            "path", "roles", "input_args", "hwaccel_args", "global_args",
        ],
        "global_args": True,
        "hwaccel_args": True,
        "input_args": True,
        "output_args": {
            "detect": True,
            "record": True,
        },
    },
    "best_image_timeout": True,
    "webui_url": True,
    "zones": ANY_KEYS,  # user-defined zone names
    "mqtt": {
        "enabled": True,
        "timestamp": True,
        "bounding_box": True,
        "crop": True,
        "height": True,
        "quality": True,
        "required_zones": True,
    },
    "ui": {
        "order": True,
        "dashboard": True,
        "review": True,
    },
    "onvif": {
        "host": True,
        "port": True,
        "user": True,
        "password": True,
        "tls_insecure": True,
        "ignore_time_mismatch": True,
        "profile": True,
        "autotracking": {
            "enabled": True,
            "calibrate_on_startup": True,
            "zooming": True,
            "zoom_factor": True,
            "track": True,
            "required_zones": True,
            "return_preset": True,
            "timeout": True,
            "movement_weights": True,
        },
    },
    "birdseye": {
        "order": True,
    },
    "triggers": ANY_KEYS,  # user-defined trigger names
    "profiles": True,  # list of profile names
    # Camera-level overrides of global sections
    "detect": {
        "enabled": True,
        "width": True,
        "height": True,
        "fps": True,
        "min_initialized": True,
        "max_disappeared": True,
        "stationary": {
            "classifier": True,
            "interval": True,
            "threshold": True,
            "max_frames": {
                "default": True,
                "objects": ANY_KEYS,
            },
        },
        "annotation_offset": True,
    },
    "objects": {
        "track": True,
        "mask": ANY_KEYS,  # user-defined mask names (new format) or string (old format)
        "filters": ANY_KEYS,  # user-defined object labels
        "genai": {
            "enabled": True,
            "use_snapshot": True,
            "prompt": True,
            "object_prompts": ANY_KEYS,
            "objects": True,
            "required_zones": True,
            "send_triggers": {
                "tracked_object_end": True,
                "after_significant_updates": True,
            },
            "debug_save_thumbnails": True,
        },
    },
    "motion": {
        "enabled": True,
        "threshold": True,
        "lightning_threshold": True,
        "skip_motion_threshold": True,
        "contour_area": True,
        "delta_alpha": True,
        "frame_alpha": True,
        "frame_height": True,
        "mask": ANY_KEYS,  # user-defined mask names or string
        "improve_contrast": True,
        "mqtt_off_delay": True,
    },
    "record": {
        "enabled": True,
        "expire_interval": True,
        "sync_recordings": True,
        "continuous": {
            "days": True,
        },
        "motion": {
            "days": True,
        },
        "export": {
            "timelapse_args": True,
            "hwaccel_args": True,
            "max_concurrent": True,
        },
        "preview": {
            "quality": True,
        },
        "alerts": {
            "pre_capture": True,
            "post_capture": True,
            "retain": {
                "days": True,
                "mode": True,
            },
        },
        "detections": {
            "pre_capture": True,
            "post_capture": True,
            "retain": {
                "days": True,
                "mode": True,
            },
        },
    },
    "snapshots": {
        "enabled": True,
        "clean_copy": True,
        "timestamp": True,
        "bounding_box": True,
        "crop": True,
        "height": True,
        "required_zones": True,
        "retain": {
            "default": True,
            "objects": ANY_KEYS,
        },
        "quality": True,
    },
    "audio": {
        "enabled": True,
        "max_not_heard": True,
        "min_volume": True,
        "num_threads": True,
        "listen": True,
        "filters": ANY_KEYS,
    },
    "birdseye_override": {  # birdseye at camera level
        "enabled": True,
        "mode": True,
        "order": True,
    },
    "live": {
        "streams": ANY_KEYS,  # label -> stream name
        "height": True,
        "quality": True,
    },
    "timestamp_style": {
        "position": True,
        "format": True,
        "color": {
            "red": True,
            "green": True,
            "blue": True,
        },
        "thickness": True,
        "effect": True,
    },
    "review": {
        "alerts": {
            "enabled": True,
            "labels": True,
            "cutoff_time": True,
            "required_zones": True,
        },
        "detections": {
            "enabled": True,
            "labels": True,
            "cutoff_time": True,
            "required_zones": True,
        },
        "genai": {
            "enabled": True,
            "alerts": True,
            "detections": True,
            "activity_context_prompt": True,
            "image_source": True,
            "additional_concerns": True,
            "preferred_language": True,
            "debug_save_thumbnails": True,
        },
    },
    "notifications": {
        "enabled": True,
        "email": True,
        "cooldown": True,
    },
    "face_recognition": {
        "enabled": True,
        "min_area": True,
    },
    "lpr": {
        "enabled": True,
        "min_area": True,
        "enhancement": True,
    },
}

# Top-level config keys
FRIGATE_VALID_KEYS = {
    "mqtt": {
        "enabled": True,
        "host": True,
        "port": True,
        "topic_prefix": True,
        "client_id": True,
        "user": True,
        "password": True,
        "tls_ca_certs": True,
        "tls_client_cert": True,
        "tls_client_key": True,
        "tls_insecure": True,
        "stats_interval": True,
        "qos": True,
    },
    "detectors": ANY_KEYS,  # user-defined detector names
    "database": {
        "path": True,
    },
    "tls": {
        "enabled": True,
    },
    "networking": {
        "ipv6": {
            "enabled": True,
        },
        "listen": {
            "internal": True,
            "external": True,
        },
    },
    "proxy": {
        "header_map": {
            "user": True,
            "role": True,
            "role_map": ANY_KEYS,
        },
        "logout_url": True,
        "auth_secret": True,
        "default_role": True,
        "separator": True,
    },
    "auth": {
        "enabled": True,
        "reset_admin_password": True,
        "cookie_name": True,
        "cookie_secure": True,
        "session_length": True,
        "refresh_time": True,
        "failed_login_rate_limit": True,
        "trusted_proxies": True,
        "hash_iterations": True,
        "roles": ANY_KEYS,
    },
    "model": {
        "path": True,
        "labelmap_path": True,
        "width": True,
        "height": True,
        "input_pixel_format": True,
        "input_tensor": True,
        "input_dtype": True,
        "model_type": True,
        "labelmap": ANY_KEYS,
        "attributes_map": ANY_KEYS,
    },
    "audio": {
        "enabled": True,
        "max_not_heard": True,
        "min_volume": True,
        "num_threads": True,
        "listen": True,
        "filters": ANY_KEYS,
    },
    "logger": {
        "default": True,
        "logs": ANY_KEYS,
    },
    "environment_vars": ANY_KEYS,
    "birdseye": {
        "enabled": True,
        "restream": True,
        "width": True,
        "height": True,
        "quality": True,
        "mode": True,
        "inactivity_threshold": True,
        "layout": {
            "scaling_factor": True,
            "max_cameras": True,
        },
        "idle_heartbeat_fps": True,
    },
    "ffmpeg": {
        "path": True,
        "global_args": True,
        "hwaccel_args": True,
        "input_args": True,
        "output_args": {
            "detect": True,
            "record": True,
        },
        "retry_interval": True,
        "apple_compatibility": True,
        "gpu": True,
    },
    "detect": {
        "enabled": True,
        "width": True,
        "height": True,
        "fps": True,
        "min_initialized": True,
        "max_disappeared": True,
        "stationary": {
            "classifier": True,
            "interval": True,
            "threshold": True,
            "max_frames": {
                "default": True,
                "objects": ANY_KEYS,
            },
        },
        "annotation_offset": True,
    },
    "objects": {
        "track": True,
        "mask": ANY_KEYS,
        "filters": ANY_KEYS,
        "genai": {
            "enabled": True,
            "use_snapshot": True,
            "prompt": True,
            "object_prompts": ANY_KEYS,
            "objects": True,
            "required_zones": True,
            "send_triggers": {
                "tracked_object_end": True,
                "after_significant_updates": True,
            },
            "debug_save_thumbnails": True,
        },
    },
    "review": {
        "alerts": {
            "enabled": True,
            "labels": True,
            "cutoff_time": True,
            "required_zones": True,
        },
        "detections": {
            "enabled": True,
            "labels": True,
            "cutoff_time": True,
            "required_zones": True,
        },
        "genai": {
            "enabled": True,
            "alerts": True,
            "detections": True,
            "activity_context_prompt": True,
            "image_source": True,
            "additional_concerns": True,
            "preferred_language": True,
            "debug_save_thumbnails": True,
        },
    },
    "motion": {
        "enabled": True,
        "threshold": True,
        "lightning_threshold": True,
        "skip_motion_threshold": True,
        "contour_area": True,
        "delta_alpha": True,
        "frame_alpha": True,
        "frame_height": True,
        "mask": ANY_KEYS,
        "improve_contrast": True,
        "mqtt_off_delay": True,
    },
    "notifications": {
        "enabled": True,
        "email": True,
        "cooldown": True,
    },
    "record": {
        "enabled": True,
        "expire_interval": True,
        "sync_recordings": True,
        "continuous": {
            "days": True,
        },
        "motion": {
            "days": True,
        },
        "export": {
            "timelapse_args": True,
            "hwaccel_args": True,
            "max_concurrent": True,
        },
        "preview": {
            "quality": True,
        },
        "alerts": {
            "pre_capture": True,
            "post_capture": True,
            "retain": {
                "days": True,
                "mode": True,
            },
        },
        "detections": {
            "pre_capture": True,
            "post_capture": True,
            "retain": {
                "days": True,
                "mode": True,
            },
        },
    },
    "snapshots": {
        "enabled": True,
        "clean_copy": True,
        "timestamp": True,
        "bounding_box": True,
        "crop": True,
        "height": True,
        "required_zones": True,
        "retain": {
            "default": True,
            "objects": ANY_KEYS,
        },
        "quality": True,
    },
    "semantic_search": {
        "enabled": True,
        "reindex": True,
        "model": True,
        "model_size": True,
        "device": True,
    },
    "face_recognition": {
        "enabled": True,
        "unknown_score": True,
        "detection_threshold": True,
        "recognition_threshold": True,
        "min_area": True,
        "min_faces": True,
        "save_attempts": True,
        "blur_confidence_filter": True,
        "model_size": True,
        "device": True,
    },
    "lpr": {
        "enabled": True,
        "device": True,
        "model_size": True,
        "detection_threshold": True,
        "min_area": True,
        "recognition_threshold": True,
        "min_plate_length": True,
        "format": True,
        "match_distance": True,
        "known_plates": ANY_KEYS,
        "enhancement": True,
        "debug_save_plates": True,
        "replace_rules": True,
    },
    "genai": ANY_KEYS,  # named providers
    "audio_transcription": {
        "enabled": True,
        "device": True,
        "model_size": True,
        "language": True,
    },
    "classification": {
        "bird": {
            "enabled": True,
            "threshold": True,
        },
        "custom": ANY_KEYS,
    },
    "go2rtc": {
        "streams": ANY_KEYS,
        "ffmpeg": ANY_KEYS,
    },
    "live": {
        "streams": ANY_KEYS,
        "height": True,
        "quality": True,
    },
    "timestamp_style": {
        "position": True,
        "format": True,
        "color": {
            "red": True,
            "green": True,
            "blue": True,
        },
        "thickness": True,
        "effect": True,
    },
    "cameras": ANY_KEYS,  # user-defined camera names, validated against CAMERA_KEYS
    "ui": {
        "timezone": True,
        "time_format": True,
        "date_style": True,
        "time_style": True,
        "unit_system": True,
    },
    "telemetry": {
        "network_interfaces": True,
        "stats": {
            "amd_gpu_stats": True,
            "intel_gpu_stats": True,
            "intel_gpu_device": True,
            "network_bandwidth": True,
        },
        "version_check": True,
    },
    "camera_groups": ANY_KEYS,  # user-defined group names
    "profiles": ANY_KEYS,  # user-defined profile names
    "version": True,  # frigatecfg internal version tracking
}

# Camera group item allowed keys
CAMERA_GROUP_KEYS = {
    "cameras": True,
    "icon": True,
    "order": True,
}

# Detector item allowed keys
DETECTOR_KEYS = {
    "type": True,
    "device": True,
    "num_threads": True,
}


def validate_keys(data: dict, allowed: dict | None, path: str = "") -> list[str]:
    """Recursively validate that all keys in data are allowed.

    Args:
        data: The config dict to validate.
        allowed: Schema dict where keys are allowed field names.
            None means any key is allowed (user-defined names).
            True means leaf value (no sub-keys expected).
            dict means nested validation.
        path: Dot-separated path for error messages.

    Returns:
        List of error messages for invalid keys.
    """
    if allowed is None:
        return []
    if not isinstance(data, dict):
        return []

    errors = []
    for key, value in data.items():
        full_path = f"{path}.{key}" if path else key

        if key not in allowed:
            errors.append(f"Invalid key: {full_path}")
            continue

        sub_allowed = allowed[key]
        if sub_allowed is True:
            # Leaf value, no further validation needed
            continue
        elif isinstance(sub_allowed, list):
            # List of dicts (e.g. ffmpeg.inputs)
            if isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        item_allowed = {k: True for k in sub_allowed}
                        errors.extend(validate_keys(item, item_allowed, f"{full_path}[{i}]"))
        elif isinstance(sub_allowed, dict):
            if isinstance(value, dict):
                errors.extend(validate_keys(value, sub_allowed, full_path))
            else:
                errors.append(f"Expected dict at {full_path}, got {type(value).__name__}")

    return errors


def validate_config(config: dict) -> list[str]:
    """Validate a full Frigate config against the schema.

    Returns list of error messages (empty = valid).
    """
    errors = validate_keys(config, FRIGATE_VALID_KEYS)

    # Validate each camera against CAMERA_KEYS
    cameras = config.get("cameras", {})
    if isinstance(cameras, dict):
        for cam_name, cam_config in cameras.items():
            if isinstance(cam_config, dict):
                cam_errors = validate_keys(cam_config, CAMERA_KEYS, f"cameras.{cam_name}")
                errors.extend(cam_errors)

    # Validate each camera group against CAMERA_GROUP_KEYS
    groups = config.get("camera_groups", {})
    if isinstance(groups, dict):
        for group_name, group_config in groups.items():
            if isinstance(group_config, dict):
                group_errors = validate_keys(group_config, CAMERA_GROUP_KEYS, f"camera_groups.{group_name}")
                errors.extend(group_errors)

    # Validate each detector against DETECTOR_KEYS
    detectors = config.get("detectors", {})
    if isinstance(detectors, dict):
        for det_name, det_config in detectors.items():
            if isinstance(det_config, dict):
                det_errors = validate_keys(det_config, DETECTOR_KEYS, f"detectors.{det_name}")
                errors.extend(det_errors)

    return errors
