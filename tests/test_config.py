"""Test suite for frigatecfg config generation.

Validates that all editable settings produce configs with valid keys
in the right places, matching the Frigate reference schema.

Run: python -m pytest tests/ -v
Or:  python -m unittest tests.test_config -v
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from frigatecfg.config_manager import (
    add_camera, rename_camera, delete_camera, reorder_cameras,
    get_cameras, get_go2rtc_streams, build_camera_streams_map,
    dump_yaml, deep_clone,
)
from frigatecfg.routes.cameras import parse_camera_from_form
from frigatecfg.routes.settings import parse_section_from_form
from frigatecfg.config_schema import SECTION_MAP, ALL_SECTIONS

from tests.mock_form import MockForm
from tests.frigate_schema import validate_config, validate_keys, CAMERA_KEYS, FRIGATE_VALID_KEYS


class TestCameraFormParser(unittest.TestCase):
    """Test that parse_camera_from_form produces valid Frigate camera configs."""

    def _validate_camera(self, camera: dict, cam_name: str = "test_cam") -> None:
        errors = validate_keys(camera, CAMERA_KEYS, f"cameras.{cam_name}")
        self.assertEqual(errors, [], f"Invalid camera keys: {errors}")

    def test_minimal_camera(self):
        """Minimal camera: just enabled."""
        form = MockForm({"enabled": "on"})
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        self.assertTrue(camera["enabled"])

    def test_full_camera_with_record(self):
        """Camera with all record settings populated."""
        form = MockForm({
            "enabled": "on",
            "type": "generic",
            "ui_order": "1",
            "record_enabled": "on",
            "record_continuous_days": "3",
            "record_motion_days": "5",
            "record_expire_interval": "30",
            "record_alerts_pre": "10",
            "record_alerts_post": "15",
            "record_alerts_retain_days": "30",
            "record_alerts_retain_mode": "motion",
            "record_detections_pre": "5",
            "record_detections_post": "10",
            "record_detections_retain_days": "7",
            "record_detections_retain_mode": "active_objects",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)

        record = camera["record"]
        self.assertTrue(record["enabled"])
        self.assertEqual(record["continuous"]["days"], 3)
        self.assertEqual(record["motion"]["days"], 5)
        self.assertEqual(record["expire_interval"], 30)
        self.assertEqual(record["alerts"]["pre_capture"], 10)
        self.assertEqual(record["alerts"]["post_capture"], 15)
        self.assertEqual(record["alerts"]["retain"]["days"], 30)
        self.assertEqual(record["alerts"]["retain"]["mode"], "motion")
        self.assertEqual(record["detections"]["pre_capture"], 5)
        self.assertEqual(record["detections"]["post_capture"], 10)
        self.assertEqual(record["detections"]["retain"]["days"], 7)
        self.assertEqual(record["detections"]["retain"]["mode"], "active_objects")

    def test_record_no_invalid_retain_key(self):
        """Ensure record.retain is never written (the bug we fixed)."""
        form = MockForm({
            "enabled": "on",
            "record_enabled": "on",
            "record_continuous_days": "0",
            "record_motion_days": "0",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        self.assertNotIn("retain", camera["record"],
                         "record.retain must not exist (only alerts.retain and detections.retain)")

    def test_camera_with_detect(self):
        """Camera with detect settings."""
        form = MockForm({
            "enabled": "on",
            "detect_enabled": "on",
            "detect_width": "1280",
            "detect_height": "720",
            "detect_fps": "5",
            "detect_min_initialized": "2",
            "detect_max_disappeared": "25",
            "detect_stationary_threshold": "50",
            "detect_stationary_interval": "50",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)

        detect = camera["detect"]
        self.assertTrue(detect["enabled"])
        self.assertEqual(detect["width"], 1280)
        self.assertEqual(detect["height"], 720)
        self.assertEqual(detect["fps"], 5)
        self.assertEqual(detect["min_initialized"], 2)
        self.assertEqual(detect["max_disappeared"], 25)
        self.assertEqual(detect["stationary"]["threshold"], 50)
        self.assertEqual(detect["stationary"]["interval"], 50)

    def test_camera_with_snapshots(self):
        """Camera with snapshot settings."""
        form = MockForm({
            "enabled": "on",
            "snapshots_enabled": "on",
            "snapshots_clean_copy": "on",
            "snapshots_timestamp": "on",
            "snapshots_bounding_box": "on",
            "snapshots_crop": "on",
            "snapshots_height": "175",
            "snapshots_quality": "70",
            "snapshots_retain_days": "10",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)

        snapshots = camera["snapshots"]
        self.assertTrue(snapshots["enabled"])
        self.assertTrue(snapshots["clean_copy"])
        self.assertTrue(snapshots["timestamp"])
        self.assertTrue(snapshots["bounding_box"])
        self.assertTrue(snapshots["crop"])
        self.assertEqual(snapshots["height"], 175)
        self.assertEqual(snapshots["quality"], 70)
        self.assertEqual(snapshots["retain"]["default"], 10)

    def test_camera_with_objects(self):
        """Camera with object tracking."""
        form = MockForm({
            "enabled": "on",
            "objects_track": ["person", "car", "dog"],
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        self.assertEqual(camera["objects"]["track"], ["person", "car", "dog"])

    def test_camera_with_live_and_webui(self):
        """Camera with live stream and webui_url."""
        form = MockForm({
            "enabled": "on",
            "webui_url": "http://10.0.0.1",
            "live_stream_name": "main",
            "best_image_timeout": "60",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        self.assertEqual(camera["webui_url"], "http://10.0.0.1")
        self.assertEqual(camera["live"]["streams"], {"main": "main"})
        self.assertEqual(camera["best_image_timeout"], 60)

    def test_camera_with_record_output_preset(self):
        """Camera with record output preset goes to ffmpeg.output_args.record."""
        form = MockForm({
            "enabled": "on",
            "record_output_preset": "preset-record-generic-audio-copy",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        self.assertEqual(
            camera["ffmpeg"]["output_args"]["record"],
            "preset-record-generic-audio-copy",
        )

    def test_camera_custom_record_no_audio(self):
        """Custom record args: no audio, 60s segments."""
        form = MockForm({
            "enabled": "on",
            "record_output_preset": "__custom__",
            "record_segment_time": "60",
            "record_audio_mode": "none",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        args = camera["ffmpeg"]["output_args"]["record"]
        self.assertIn("-segment_time 60", args)
        self.assertIn("-an", args)
        self.assertNotIn("-c:a", args)

    def test_camera_custom_record_audio_copy(self):
        """Custom record args: audio copy, 30s segments."""
        form = MockForm({
            "enabled": "on",
            "record_output_preset": "__custom__",
            "record_segment_time": "30",
            "record_audio_mode": "copy",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        args = camera["ffmpeg"]["output_args"]["record"]
        self.assertIn("-segment_time 30", args)
        self.assertIn("-c copy", args)
        self.assertNotIn("-an", args)

    def test_camera_custom_record_audio_aac(self):
        """Custom record args: audio AAC, 45s segments."""
        form = MockForm({
            "enabled": "on",
            "record_output_preset": "__custom__",
            "record_segment_time": "45",
            "record_audio_mode": "aac",
        })
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        args = camera["ffmpeg"]["output_args"]["record"]
        self.assertIn("-segment_time 45", args)
        self.assertIn("-c:v copy", args)
        self.assertIn("-c:a aac", args)

    def test_camera_custom_record_segment_clamped(self):
        """Segment time clamped to 10-60 range."""
        form = MockForm({
            "enabled": "on",
            "record_output_preset": "__custom__",
            "record_segment_time": "120",
            "record_audio_mode": "none",
        })
        camera = parse_camera_from_form(form)
        args = camera["ffmpeg"]["output_args"]["record"]
        self.assertIn("-segment_time 60", args)

    def test_camera_custom_record_default_segment(self):
        """Custom with no segment_time defaults to 10."""
        form = MockForm({
            "enabled": "on",
            "record_output_preset": "__custom__",
            "record_audio_mode": "none",
        })
        camera = parse_camera_from_form(form)
        args = camera["ffmpeg"]["output_args"]["record"]
        self.assertIn("-segment_time 10", args)

    def test_camera_disabled_record(self):
        """When record_enabled is not checked, record.enabled is False."""
        form = MockForm({"enabled": "on"})
        camera = parse_camera_from_form(form)
        self._validate_camera(camera)
        self.assertFalse(camera["record"]["enabled"])
        # No continuous/motion/alerts/detections when disabled
        self.assertNotIn("continuous", camera["record"])
        self.assertNotIn("motion", camera["record"])
        self.assertNotIn("alerts", camera["record"])
        self.assertNotIn("detections", camera["record"])


class TestSettingsFormParser(unittest.TestCase):
    """Test that parse_section_from_form produces valid Frigate section configs."""

    def _validate_section(self, section_name: str, section_data: dict) -> None:
        """Validate section data against the Frigate schema."""
        # For dict collections (detectors, camera_groups, environment_vars),
        # validate each item
        if section_name == "detectors":
            from tests.frigate_schema import DETECTOR_KEYS
            for name, item in section_data.items():
                errors = validate_keys(item, DETECTOR_KEYS, f"detectors.{name}")
                self.assertEqual(errors, [], f"Invalid detector {name}: {errors}")
        elif section_name == "camera_groups":
            from tests.frigate_schema import CAMERA_GROUP_KEYS
            for name, item in section_data.items():
                errors = validate_keys(item, CAMERA_GROUP_KEYS, f"camera_groups.{name}")
                self.assertEqual(errors, [], f"Invalid camera group {name}: {errors}")
        else:
            # Validate against the top-level schema for this section
            section_schema = FRIGATE_VALID_KEYS.get(section_name)
            if section_schema and isinstance(section_schema, dict):
                errors = validate_keys(section_data, section_schema, section_name)
                self.assertEqual(errors, [], f"Invalid section {section_name}: {errors}")

    def test_mqtt_section(self):
        """MQTT section produces valid config."""
        form = MockForm({
            "mqtt_enabled": "on",
            "mqtt_host": "mqtt.local",
            "mqtt_port": "1883",
            "mqtt_topic_prefix": "frigate",
            "mqtt_client_id": "frigate",
            "mqtt_user": "user",
            "mqtt_password": "pass",
            "mqtt_stats_interval": "60",
            "mqtt_qos": "0",
        })
        section = SECTION_MAP["mqtt"]
        result = parse_section_from_form(section, form, prefix="mqtt")
        self._validate_section("mqtt", result)
        self.assertTrue(result["enabled"])
        self.assertEqual(result["host"], "mqtt.local")

    def test_record_section(self):
        """Record section produces valid config with no top-level retain."""
        form = MockForm({
            "record_enabled": "on",
            "record_expire_interval": "60",
            "record_continuous_days": "0",
            "record_motion_days": "0",
            "record_alerts_pre": "5",
            "record_alerts_post": "5",
            "record_alerts_retain_days": "10",
            "record_alerts_retain_mode": "motion",
            "record_detections_pre": "5",
            "record_detections_post": "5",
            "record_detections_retain_days": "10",
            "record_detections_retain_mode": "motion",
        })
        section = SECTION_MAP["record"]
        result = parse_section_from_form(section, form, prefix="record")
        self._validate_section("record", result)
        self.assertNotIn("retain", result, "record.retain must not exist at top level")

    def test_detect_section(self):
        """Detect section produces valid config."""
        form = MockForm({
            "detect_enabled": "on",
            "detect_width": "1280",
            "detect_height": "720",
            "detect_fps": "5",
            "detect_min_initialized": "2",
            "detect_max_disappeared": "25",
            "detect_stationary_classifier": "on",
            "detect_stationary_interval": "50",
            "detect_stationary_threshold": "50",
        })
        section = SECTION_MAP["detect"]
        result = parse_section_from_form(section, form, prefix="detect")
        self._validate_section("detect", result)

    def test_detectors_section(self):
        """Detectors section produces valid config."""
        form = MockForm({
            "detectors_key_0": "coral",
            "detectors_0_type": "edgetpu",
            "detectors_0_device": "usb",
        })
        section = SECTION_MAP["detectors"]
        result = parse_section_from_form(section, form, prefix="detectors")
        self._validate_section("detectors", result)
        self.assertIn("coral", result)
        self.assertEqual(result["coral"]["type"], "edgetpu")

    def test_camera_groups_section(self):
        """Camera groups section produces valid config."""
        form = MockForm({
            "camera_groups_key_0": "interior",
            "camera_groups_0_cameras": ["kitchen", "livingroom"],
            "camera_groups_0_icon": "LuDoorClosed",
            "camera_groups_0_order": "1",
        })
        section = SECTION_MAP["camera_groups"]
        result = parse_section_from_form(section, form, prefix="camera_groups")
        self._validate_section("camera_groups", result)
        self.assertIn("interior", result)
        self.assertEqual(result["interior"]["cameras"], ["kitchen", "livingroom"])

    def test_snapshots_section(self):
        """Snapshots section produces valid config."""
        form = MockForm({
            "snapshots_enabled": "on",
            "snapshots_clean_copy": "on",
            "snapshots_timestamp": "on",
            "snapshots_bounding_box": "on",
            "snapshots_crop": "on",
            "snapshots_height": "175",
            "snapshots_quality": "70",
            "snapshots_retain_default": "10",
        })
        section = SECTION_MAP["snapshots"]
        result = parse_section_from_form(section, form, prefix="snapshots")
        self._validate_section("snapshots", result)

    def test_ffmpeg_section(self):
        """FFmpeg section produces valid config."""
        form = MockForm({
            "ffmpeg_hwaccel_args": "preset-nvidia",
            "ffmpeg_input_args": "preset-rtsp-generic",
            "ffmpeg_output_args_detect": "-threads 2 -f rawvideo -pix_fmt yuv420p",
            "ffmpeg_output_args_record": "preset-record-generic",
        })
        section = SECTION_MAP["ffmpeg"]
        result = parse_section_from_form(section, form, prefix="ffmpeg")
        self._validate_section("ffmpeg", result)

    def test_all_sections_validate(self):
        """Every section in ALL_SECTIONS can be parsed with minimal data without producing invalid keys."""
        for section in ALL_SECTIONS:
            with self.subTest(section=section.name):
                form = MockForm()
                result = parse_section_from_form(section, form, prefix=section.name)
                # Empty results are valid (no fields set)
                if result:
                    self._validate_section(section.name, result)


class TestConfigManager(unittest.TestCase):
    """Test config_manager operations produce valid configs."""

    def _base_config(self) -> dict:
        """Create a minimal valid Frigate config for testing."""
        return {
            "mqtt": {"enabled": True, "host": "mqtt.local"},
            "cameras": {},
            "go2rtc": {"streams": {}},
        }

    def test_add_camera_validates(self):
        """add_camera produces valid config."""
        config = self._base_config()
        camera_data = {
            "enabled": True,
            "type": "generic",
            "ffmpeg": {
                "inputs": [
                    {"path": "rtsp://127.0.0.1:8554/front_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
                    {"path": "rtsp://127.0.0.1:8554/front_sub", "input_args": "preset-rtsp-restream", "roles": ["detect"]},
                ],
            },
            "detect": {"enabled": True, "fps": 5},
        }
        streams = {
            "front_main": ["rtsp://user:pass@10.0.0.1:554/stream1"],
            "front_sub": ["rtsp://user:pass@10.0.0.1:554/stream2"],
        }
        add_camera(config, "front", camera_data, streams=streams)
        errors = validate_config(config)
        self.assertEqual(errors, [], f"Invalid config after add_camera: {errors}")

    def test_add_camera_with_full_record(self):
        """add_camera with full record settings validates."""
        config = self._base_config()
        camera_data = {
            "enabled": True,
            "type": "generic",
            "record": {
                "enabled": True,
                "continuous": {"days": 3},
                "motion": {"days": 5},
                "alerts": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {"days": 30, "mode": "motion"},
                },
                "detections": {
                    "pre_capture": 5,
                    "post_capture": 5,
                    "retain": {"days": 10, "mode": "active_objects"},
                },
            },
            "ffmpeg": {
                "inputs": [
                    {"path": "rtsp://127.0.0.1:8554/cam_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
                ],
            },
        }
        add_camera(config, "cam", camera_data, streams={"cam_main": ["rtsp://10.0.0.1/stream"]})
        errors = validate_config(config)
        self.assertEqual(errors, [], f"Invalid config: {errors}")

    def test_rename_camera_validates(self):
        """rename_camera produces valid config."""
        config = self._base_config()
        camera_data = {
            "enabled": True,
            "ffmpeg": {
                "inputs": [
                    {"path": "rtsp://127.0.0.1:8554/old_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
                ],
            },
        }
        add_camera(config, "old", camera_data, streams={"old_main": ["rtsp://10.0.0.1/stream"]})
        rename_camera(config, "old", "new")
        errors = validate_config(config)
        self.assertEqual(errors, [], f"Invalid config after rename: {errors}")
        self.assertIn("new", config["cameras"])
        self.assertNotIn("old", config["cameras"])
        self.assertIn("new_main", config["go2rtc"]["streams"])

    def test_delete_camera_validates(self):
        """delete_camera produces valid config."""
        config = self._base_config()
        camera_data = {
            "enabled": True,
            "ffmpeg": {
                "inputs": [
                    {"path": "rtsp://127.0.0.1:8554/cam_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
                ],
            },
        }
        add_camera(config, "cam", camera_data, streams={"cam_main": ["rtsp://10.0.0.1/stream"]})
        delete_camera(config, "cam")
        errors = validate_config(config)
        self.assertEqual(errors, [], f"Invalid config after delete: {errors}")
        self.assertNotIn("cam", config["cameras"])

    def test_reorder_cameras_validates(self):
        """reorder_cameras produces valid config."""
        config = self._base_config()
        for name in ["cam_a", "cam_b", "cam_c"]:
            add_camera(config, name, {
                "enabled": True,
                "ffmpeg": {"inputs": [
                    {"path": f"rtsp://127.0.0.1:8554/{name}_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
                ]},
            }, streams={f"{name}_main": ["rtsp://10.0.0.1/stream"]})
        reorder_cameras(config, ["cam_c", "cam_a", "cam_b"])
        errors = validate_config(config)
        self.assertEqual(errors, [], f"Invalid config after reorder: {errors}")
        self.assertEqual(list(config["cameras"].keys()), ["cam_c", "cam_a", "cam_b"])

    def test_build_camera_streams_map(self):
        """build_camera_streams_map correctly associates streams."""
        config = {
            "cameras": {"kitchen": {}, "kitchen_door": {}, "livingroom": {}},
            "go2rtc": {"streams": {
                "kitchen_main": [""], "kitchen_sub": [""],
                "kitchen_door_main": [""], "kitchen_door_sub": [""],
                "livingroom_main": [""], "livingroom_sub": [""],
            }},
        }
        result = build_camera_streams_map(config)
        self.assertEqual(result["kitchen"], ["kitchen_main", "kitchen_sub"])
        self.assertEqual(result["kitchen_door"], ["kitchen_door_main", "kitchen_door_sub"])
        self.assertEqual(result["livingroom"], ["livingroom_main", "livingroom_sub"])
        # kitchen should NOT have kitchen_door streams
        self.assertNotIn("kitchen_door_main", result["kitchen"])

    def test_dump_yaml_roundtrip(self):
        """dump_yaml produces valid YAML that can be re-parsed."""
        import yaml
        config = self._base_config()
        add_camera(config, "test", {
            "enabled": True,
            "type": "generic",
            "ffmpeg": {"inputs": [
                {"path": "rtsp://127.0.0.1:8554/test_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
            ]},
            "record": {
                "enabled": True,
                "continuous": {"days": 0},
                "alerts": {"retain": {"days": 30, "mode": "motion"}},
            },
        }, streams={"test_main": ["rtsp://10.0.0.1/stream"]})
        yaml_str = dump_yaml(config)
        reparsed = yaml.safe_load(yaml_str)
        errors = validate_config(reparsed)
        self.assertEqual(errors, [], f"Invalid config after YAML roundtrip: {errors}")


class TestFullConfigValidation(unittest.TestCase):
    """Test that a complete config with all sections validates."""

    def test_full_config_from_user_example(self):
        """Validate the user's actual config from the bug report."""
        config = {
            "mqtt": {
                "enabled": True, "host": "192.168.100.30", "port": 1883,
                "topic_prefix": "frigate", "client_id": "frigate",
                "user": "mqtt", "password": "secret", "stats_interval": 60, "qos": 0,
            },
            "ffmpeg": {"hwaccel_args": "preset-nvidia"},
            "detectors": {"coral": {"type": "edgetpu", "device": "usb"}},
            "go2rtc": {"streams": {
                "kitchen_main": ["rtsp://user:pass@10.20.20.12:554/main"],
                "kitchen_sub": ["rtsp://user:pass@10.20.20.12:554/sub"],
            }},
            "cameras": {
                "kitchen": {
                    "enabled": True,
                    "ffmpeg": {"inputs": [
                        {"path": "rtsp://127.0.0.1:8554/kitchen_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
                        {"path": "rtsp://127.0.0.1:8554/kitchen_sub", "input_args": "preset-rtsp-restream", "roles": ["detect"]},
                    ]},
                    "record": {"enabled": False},
                    "detect": {"enabled": True, "fps": 5, "min_initialized": 2, "max_disappeared": 25,
                               "stationary": {"threshold": 50, "interval": 50}},
                    "objects": {"track": ["person", "car"]},
                    "snapshots": {"enabled": False},
                    "best_image_timeout": 60,
                    "ui": {"order": 0},
                    "type": "generic",
                },
                "addition-e1pro-01": {
                    "enabled": True,
                    "type": "generic",
                    "ffmpeg": {"inputs": [
                        {"path": "rtsp://127.0.0.1:8554/addition-e1pro-01_main", "input_args": "preset-rtsp-restream", "roles": ["record"]},
                        {"path": "rtsp://127.0.0.1:8554/addition-e1pro-01_sub", "input_args": "preset-rtsp-restream", "roles": ["detect"]},
                    ]},
                    "record": {
                        "enabled": True,
                        "continuous": {"days": 0},
                        "motion": {"days": 0},
                        "expire_interval": 60,
                        "alerts": {
                            "pre_capture": 5, "post_capture": 5,
                            "retain": {"days": 10, "mode": "motion"},
                        },
                        "detections": {
                            "pre_capture": 5, "post_capture": 5,
                            "retain": {"days": 10, "mode": "active_objects"},
                        },
                    },
                    "detect": {"enabled": True, "fps": 5, "min_initialized": 2, "max_disappeared": 25,
                               "stationary": {"threshold": 50, "interval": 50}},
                    "objects": {"track": ["person"]},
                    "snapshots": {"enabled": False},
                    "best_image_timeout": 60,
                    "ui": {"order": 0},
                    "webui_url": "http://10.20.20.13",
                },
            },
            "version": "0.17-0",
            "camera_groups": {
                "interior": {
                    "order": 1, "icon": "LuDoorClosed",
                    "cameras": ["kitchen", "addition-e1pro-01"],
                },
            },
        }
        errors = validate_config(config)
        self.assertEqual(errors, [], f"User config has errors: {errors}")

    def test_config_with_invalid_record_retain(self):
        """Config with the old bug (record.retain) should be caught."""
        config = {
            "cameras": {
                "test": {
                    "enabled": True,
                    "record": {
                        "enabled": True,
                        "retain": {"days": 0, "mode": "active_objects"},
                    },
                    "ffmpeg": {"inputs": [
                        {"path": "rtsp://127.0.0.1:8554/test_main", "roles": ["record"]},
                    ]},
                },
            },
        }
        errors = validate_config(config)
        self.assertTrue(any("retain" in e for e in errors),
                        f"Should detect invalid record.retain key: {errors}")

    def test_simulated_full_edit_workflow(self):
        """Simulate editing a camera with all fields, then validate the full config."""
        # Step 1: Create camera via form
        form = MockForm({
            "enabled": "on",
            "type": "generic",
            "ui_order": "0",
            "objects_track": ["person", "car", "dog"],
            "record_enabled": "on",
            "record_continuous_days": "0",
            "record_motion_days": "0",
            "record_expire_interval": "60",
            "record_alerts_pre": "5",
            "record_alerts_post": "5",
            "record_alerts_retain_days": "30",
            "record_alerts_retain_mode": "motion",
            "record_detections_pre": "5",
            "record_detections_post": "5",
            "record_detections_retain_days": "10",
            "record_detections_retain_mode": "motion",
            "detect_enabled": "on",
            "detect_fps": "5",
            "detect_min_initialized": "2",
            "detect_max_disappeared": "25",
            "detect_stationary_threshold": "50",
            "detect_stationary_interval": "50",
            "snapshots_enabled": "on",
            "snapshots_clean_copy": "on",
            "snapshots_timestamp": "on",
            "snapshots_bounding_box": "on",
            "snapshots_height": "175",
            "snapshots_quality": "70",
            "snapshots_retain_days": "10",
            "webui_url": "http://10.0.0.1",
            "best_image_timeout": "60",
            "live_stream_name": "main",
            "record_output_preset": "preset-record-generic-audio-copy",
        })
        camera = parse_camera_from_form(form)

        # Step 2: Add to config
        config = {
            "mqtt": {"enabled": True, "host": "mqtt.local"},
            "go2rtc": {"streams": {}},
            "cameras": {},
        }
        add_camera(config, "front_door", camera, streams={
            "front_door_main": ["rtsp://user:pass@10.0.0.1:554/main"],
            "front_door_sub": ["rtsp://user:pass@10.0.0.1:554/sub"],
        })

        # Step 3: Validate full config
        errors = validate_config(config)
        self.assertEqual(errors, [], f"Full config from workflow has errors: {errors}")

        # Step 4: YAML roundtrip
        import yaml
        yaml_str = dump_yaml(config)
        reparsed = yaml.safe_load(yaml_str)
        errors = validate_config(reparsed)
        self.assertEqual(errors, [], f"Config invalid after YAML roundtrip: {errors}")


if __name__ == "__main__":
    unittest.main()
