"""Camera brand database: ports, RTSP URL templates, detection rules, suggested settings."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote


BRAND_DATABASE: dict[str, dict[str, Any]] = {
    "reolink": {
        "name": "Reolink",
        "common_ports": [80, 443, 554, 9000],
        "identifying_ports": [9000],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/h264Preview_01_main",
            "sub": "rtsp://{user}:{password}@{ip}:554/h264Preview_01_sub",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Reolink requires RTSP to be enabled in camera web UI. Default password is set during first setup.",
    },
    "amcrest": {
        "name": "Amcrest",
        "common_ports": [80, 443, 554, 37777, 7777],
        "identifying_ports": [37777, 7777],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0",
            "sub": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Amcrest uses Dahua protocol. Port 37777 is proprietary. Default password set during setup.",
    },
    "dahua": {
        "name": "Dahua",
        "common_ports": [80, 443, 554, 37777, 5000],
        "identifying_ports": [37777],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0",
            "sub": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1",
        },
        "default_credentials": {"user": "admin", "pass": "admin"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Dahua owns Amcrest. Same RTSP URL format. Port 37777 is proprietary Dahua protocol.",
    },
    "hikvision": {
        "name": "Hikvision",
        "common_ports": [80, 443, 554, 8000, 8080],
        "identifying_ports": [8000],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/101",
            "sub": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/102",
        },
        "default_credentials": {"user": "admin", "pass": "12345"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Hikvision uses ISAPI for HTTP endpoints. Channel format: 1XX (101=main, 102=sub).",
    },
    "hilook": {
        "name": "HiLook",
        "common_ports": [80, 443, 554, 8000],
        "identifying_ports": [8000],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/101",
            "sub": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/102",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "HiLook is Hikvision's budget brand. Same RTSP URL format and port layout.",
    },
    "vstarcam": {
        "name": "VStarcam / O-KAM",
        "common_ports": [80, 554, 10080, 10554],
        "identifying_ports": [10080, 10554],
        "onvif_port": 10080,
        "rtsp_port": 10554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_0",
            "sub": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_1",
        },
        "default_credentials": {"user": "admin", "pass": "888888"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "O-KAM Pro and VStarcam share firmware. Default pass is 888888 (6-digit) or 88888888 (8-digit).",
    },
    "foscam": {
        "name": "Foscam",
        "common_ports": [80, 443, 554, 88, 8080],
        "identifying_ports": [88],
        "onvif_port": 88,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/videoMain",
            "sub": "rtsp://{user}:{password}@{ip}:554/videoSub",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Foscam often uses port 88 for web interface. Some models use /11 for main, /12 for sub.",
    },
    "tp_link_tapo": {
        "name": "TP-Link Tapo",
        "common_ports": [80, 443, 554, 1024, 2020],
        "identifying_ports": [1024, 2020],
        "onvif_port": 2020,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/stream1",
            "sub": "rtsp://{user}:{password}@{ip}:554/stream2",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Tapo cameras require RTSP/video streaming to be enabled in Tapo app. Uses account credentials, not device admin.",
    },
    "wyze": {
        "name": "Wyze",
        "common_ports": [80, 554, 1935],
        "identifying_ports": [1935],
        "onvif_port": None,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/live",
            "sub": "rtsp://{user}:{password}@{ip}:554/live_sub",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Wyze requires firmware mod or RTSP firmware. Not all models support RTSP.",
    },
    "lorex": {
        "name": "Lorex",
        "common_ports": [80, 443, 554, 8000, 35000],
        "identifying_ports": [35000],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/channel1",
            "sub": "rtsp://{user}:{password}@{ip}:554/channel1_sub",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Lorex uses Dahua hardware. Some models use Dahua URL format. Port 35000 is Lorex-specific.",
    },
    "swann": {
        "name": "Swann",
        "common_ports": [80, 443, 554, 9000, 18715],
        "identifying_ports": [18715],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/ch01/0",
            "sub": "rtsp://{user}:{password}@{ip}:554/ch01/1",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Swann uses Hikvision hardware on many models. URL format varies by model.",
    },
    "ubiquiti_unifi": {
        "name": "Ubiquiti UniFi Protect",
        "common_ports": [80, 443, 554, 7080, 7443],
        "identifying_ports": [7080, 7443],
        "onvif_port": None,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/s0",
            "sub": "rtsp://{user}:{password}@{ip}:554/s1",
        },
        "default_credentials": {"user": "ubnt", "pass": "ubnt"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "UniFi Protect cameras stream through the NVR, not directly. Use NVR IP, not camera IP.",
    },
    "axis": {
        "name": "Axis Communications",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/axis-media/media.amp",
            "sub": "rtsp://{user}:{password}@{ip}:554/axis-media/media.amp?streamprofile=sub",
        },
        "default_credentials": {"user": "root", "pass": "pass"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Axis uses VAPIX API. RTSP path may include stream profile name. Default pass set via one-time password.",
    },
    "bosch": {
        "name": "Bosch Security",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554",
            "sub": "rtsp://{user}:{password}@{ip}:554?stream=2",
        },
        "default_credentials": {"user": "service", "pass": "service"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Bosch uses RCP+ API. Stream selection via query parameter.",
    },
    "vivotek": {
        "name": "Vivotek",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/live.sdp",
            "sub": "rtsp://{user}:{password}@{ip}:554/live2.sdp",
        },
        "default_credentials": {"user": "root", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Vivotek uses .sdp stream paths. live.sdp = main, live2.sdp = sub.",
    },
    "geovision": {
        "name": "GeoVision",
        "common_ports": [80, 443, 554, 1000, 4550],
        "identifying_ports": [4550, 1000],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/channel1",
            "sub": "rtsp://{user}:{password}@{ip}:554/channel2",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "GeoVision uses port 4550 for proprietary protocol. Channel numbering starts at 1.",
    },
    "trendnet": {
        "name": "TRENDnet",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/live/channel0_0",
            "sub": "rtsp://{user}:{password}@{ip}:554/live/channel0_1",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "TRENDnet uses channel_X_Y format. 0_0 = main, 0_1 = sub.",
    },
    "d_link": {
        "name": "D-Link",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/live/ch00_0",
            "sub": "rtsp://{user}:{password}@{ip}:554/live/ch00_1",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "D-Link URL format varies by model. Some use /play1.sdp format.",
    },
    "imou": {
        "name": "Imou",
        "common_ports": [80, 443, 554, 37777],
        "identifying_ports": [37777],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0",
            "sub": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Imou is Dahua consumer brand. Same RTSP URL format as Dahua.",
    },
    "ezviz": {
        "name": "Ezviz",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/h264/ch1/main/av_stream",
            "sub": "rtsp://{user}:{password}@{ip}:554/h264/ch1/sub/av_stream",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Ezviz is Hikvision consumer brand. RTSP must be enabled via Ezviz app. Uses verification code as password.",
    },
    "wansview": {
        "name": "Wansview",
        "common_ports": [80, 443, 554, 8080, 10554],
        "identifying_ports": [10554],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/live/ch00_0",
            "sub": "rtsp://{user}:{password}@{ip}:554/live/ch00_1",
        },
        "default_credentials": {"user": "admin", "pass": "123456"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Wansview uses similar format to D-Link. Default pass is 123456.",
    },
    "annke": {
        "name": "Annke",
        "common_ports": [80, 443, 554, 8000, 8080],
        "identifying_ports": [8000],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/101",
            "sub": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/102",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Annke uses Hikvision hardware. Same RTSP URL format.",
    },
    "zosi": {
        "name": "ZOSI",
        "common_ports": [80, 443, 554, 8000, 37777],
        "identifying_ports": [37777],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=0",
            "sub": "rtsp://{user}:{password}@{ip}:554/cam/realmonitor?channel=1&subtype=1",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "ZOSI uses Dahua hardware on many models.",
    },
    "instar": {
        "name": "INSTAR",
        "common_ports": [80, 443, 554, 8080, 8888],
        "identifying_ports": [8888],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/11",
            "sub": "rtsp://{user}:{password}@{ip}:554/12",
        },
        "default_credentials": {"user": "admin", "pass": "instar"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "INSTAR uses /11 for main, /12 for sub stream. Default pass is 'instar'.",
    },
    "acti": {
        "name": "ACTi",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554",
            "sub": "rtsp://{user}:{password}@{ip}:554?stream=2",
        },
        "default_credentials": {"user": "Admin", "pass": "123456"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "ACTi uses query parameter for stream selection. Default user is 'Admin' (capital A).",
    },
    "pelco": {
        "name": "Pelco (Sarix)",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/stream1",
            "sub": "rtsp://{user}:{password}@{ip}:554/stream2",
        },
        "default_credentials": {"user": "admin", "pass": "admin"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Pelco Sarix uses simple streamN path format.",
    },
    "panasonic": {
        "name": "Panasonic (WV)",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/nphMpegVideo/11",
            "sub": "rtsp://{user}:{password}@{ip}:554/nphMpegVideo/12",
        },
        "default_credentials": {"user": "admin", "pass": "12345"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Panasonic uses nphMpegVideo path. /11 = main, /12 = sub.",
    },
    "sony": {
        "name": "Sony (IPELA)",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [8080],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/MPEG-4/ch01/main",
            "sub": "rtsp://{user}:{password}@{ip}:554/MPEG-4/ch01/sub",
        },
        "default_credentials": {"user": "admin", "pass": "admin"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Sony IPELA cameras use MPEG-4 path format.",
    },
    "sricam": {
        "name": "Sricam / SriHome",
        "common_ports": [80, 554, 8080, 9000],
        "identifying_ports": [9000],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/live/ch00_0",
            "sub": "rtsp://{user}:{password}@{ip}:554/live/ch00_1",
        },
        "default_credentials": {"user": "admin", "pass": "888888"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Sricam/SriHome default pass is 888888. Similar to VStarcam.",
    },
    "iegeek": {
        "name": "ieGeek",
        "common_ports": [80, 554, 8080, 10080, 10554],
        "identifying_ports": [10080, 10554],
        "onvif_port": 10080,
        "rtsp_port": 10554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_0",
            "sub": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_1",
        },
        "default_credentials": {"user": "admin", "pass": "888888"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "ieGeek uses VStarcam/O-KAM firmware. Same URL format and default credentials.",
    },
    "besder": {
        "name": "BESDER",
        "common_ports": [80, 554, 8080, 10080, 10554],
        "identifying_ports": [10080, 10554],
        "onvif_port": 10080,
        "rtsp_port": 10554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_0",
            "sub": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_1",
        },
        "default_credentials": {"user": "admin", "pass": "888888"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "BESDER uses same firmware as VStarcam/ieGeek. Same URL format.",
    },
    "boavision": {
        "name": "Boavision",
        "common_ports": [80, 554, 8080, 10080, 10554],
        "identifying_ports": [10080, 10554],
        "onvif_port": 10080,
        "rtsp_port": 10554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_0",
            "sub": "rtsp://{user}:{password}@{ip}:10554/tcp/av0_1",
        },
        "default_credentials": {"user": "admin", "pass": "888888"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Boavision uses same firmware family as VStarcam/ieGeek.",
    },
    "eufy": {
        "name": "Eufy (Anker)",
        "common_ports": [80, 443, 554, 1024],
        "identifying_ports": [1024],
        "onvif_port": None,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/101",
            "sub": "rtsp://{user}:{password}@{ip}:554/Streaming/Channels/102",
        },
        "default_credentials": {"user": "admin", "pass": ""},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Eufy uses Hikvision-compatible firmware on some models. RTSP must be enabled in Eufy app.",
    },
    "goulight": {
        "name": "Generic ONVIF",
        "common_ports": [80, 443, 554, 8080],
        "identifying_ports": [],
        "onvif_port": 80,
        "rtsp_port": 554,
        "rtsp_url_templates": {
            "main": "rtsp://{user}:{password}@{ip}:554/onvif1",
            "sub": "rtsp://{user}:{password}@{ip}:554/onvif2",
        },
        "default_credentials": {"user": "admin", "pass": "admin"},
        "suggested_settings": {
            "type": "generic",
            "ffmpeg": {"input_args": "preset-rtsp-restream"},
        },
        "notes": "Generic fallback for ONVIF-compatible cameras. Use ONVIF GetStreamUri for accurate URLs.",
    },
}


def _load_custom_brands() -> dict[str, dict[str, Any]]:
    """Load custom/override brands from DB and merge with built-in brands."""
    try:
        from . import models
        custom_rows = models.get_all_custom_brands()
    except Exception:
        return {}

    merged: dict[str, dict[str, Any]] = {}
    for row in custom_rows:
        import json
        key = row["brand_key"]
        data = json.loads(row["brand_data"])
        is_override = bool(row["is_override"])

        if is_override and key in BRAND_DATABASE:
            # Merge override into built-in brand
            base = dict(BRAND_DATABASE[key])
            for field in ["common_ports", "identifying_ports"]:
                if field in data:
                    base[field] = sorted(set(base.get(field, []) + data[field]))
            for field in ["name", "onvif_port", "rtsp_port", "rtsp_url_templates",
                          "default_credentials", "suggested_settings", "notes"]:
                if field in data:
                    base[field] = data[field]
            base["_custom"] = True
            base["_is_override"] = True
            merged[key] = base
        else:
            # New custom brand
            data["_custom"] = True
            data["_is_override"] = False
            merged[key] = data
    return merged


def _get_merged_brands() -> dict[str, dict[str, Any]]:
    """Get built-in brands merged with custom/override brands from DB."""
    merged = dict(BRAND_DATABASE)
    merged.update(_load_custom_brands())
    return merged


def _get_all_scan_ports() -> list[int]:
    """Get all scan ports from merged brand database."""
    brands = _get_merged_brands()
    return sorted(set(
        port for brand in brands.values()
        for port in brand.get("common_ports", [])
    ))


def get_brand_by_key(key: str) -> dict[str, Any] | None:
    return _get_merged_brands().get(key)


def get_all_brands() -> dict[str, dict[str, Any]]:
    return _get_merged_brands()


def detect_brand_from_ports(open_ports: list[int]) -> list[tuple[str, dict[str, Any], int]]:
    """Detect possible brands from open ports. Returns list of (brand_key, brand_info, match_score).

    Scoring:
    - Identifying port match: +10 (strong signal, e.g. 37777, 10080, 9000)
    - Common port match: +1 (weak signal, e.g. 80, 443)
    - Minimum score of 2 required — filters out devices with only generic web ports
    """
    brands = _get_merged_brands()
    matches = []
    for key, brand in brands.items():
        score = 0
        for port in brand.get("identifying_ports", []):
            if port in open_ports:
                score += 10
        for port in brand.get("common_ports", []):
            if port in open_ports:
                score += 1
        if score >= 2:
            matches.append((key, brand, score))
    matches.sort(key=lambda x: x[2], reverse=True)
    return matches


def get_camera_indicative_ports() -> set[int]:
    """Return ports that strongly indicate a camera device.

    Includes RTSP (554) and all brand identifying ports.
    Used to filter network scan results — devices without any of these
    are almost certainly not cameras (routers, servers, IoT, etc.).
    """
    brands = _get_merged_brands()
    ports = {554}  # RTSP — universal camera indicator
    for brand in brands.values():
        ports.update(brand.get("identifying_ports", []))
    return ports


def format_rtsp_url(template: str, ip: str, user: str, password: str) -> str:
    """Format an RTSP URL template with connection details.

    URL-encodes username and password to handle special characters
    like @, :, /, # that would break the RTSP URL structure.
    """
    safe_user = quote(user, safe="")
    safe_pass = quote(password, safe="")
    return template.format(user=safe_user, password=safe_pass, ip=ip)


def get_brand_rtsp_urls(brand_key: str, ip: str, user: str, password: str) -> dict[str, str]:
    """Get suggested RTSP URLs for a brand."""
    brand = get_brand_by_key(brand_key)
    if not brand:
        return {}
    urls = {}
    for stream_type, template in brand.get("rtsp_url_templates", {}).items():
        urls[stream_type] = format_rtsp_url(template, ip, user, password)
    return urls
