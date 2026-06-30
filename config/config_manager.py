"""
config/config_manager.py
Saves and loads user settings as JSON.
"""
import json
import os

DEFAULT_CONFIG = {
    "profile_name": "Balanced",
    "smooth_alpha": 0.35,
    "hand_weight": 0.75,
    "detection_confidence": 0.7,
    "tracking_confidence": 0.5,
    "click_cooldown": 0.6,
    "dwell_enabled": False,
    "dwell_seconds": 1.5,
    "camera_index": 0,
    "gaze_calibration": {
        "min_x": 0.35, "max_x": 0.65,
        "min_y": 0.30, "max_y": 0.70,
    },
    "active_modules": {
        "hand": True,
        "eye": True,
    }
}

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "user_profiles", "default.json")

PROFILE_PRESETS = {
    "Balanced": {
        "smooth_alpha": 0.35,
        "hand_weight": 0.75,
        "click_cooldown": 0.6,
        "dwell_enabled": False,
        "dwell_seconds": 1.5,
        "active_modules": {"hand": True, "eye": True},
    },
    "Hand Only": {
        "smooth_alpha": 0.30,
        "hand_weight": 1.0,
        "click_cooldown": 0.7,
        "dwell_enabled": False,
        "dwell_seconds": 1.5,
        "active_modules": {"hand": True, "eye": False},
    },
    "Eye Only": {
        "smooth_alpha": 0.25,
        "hand_weight": 0.0,
        "click_cooldown": 0.9,
        "dwell_enabled": True,
        "dwell_seconds": 1.8,
        "active_modules": {"hand": False, "eye": True},
    },
    "Accessibility": {
        "smooth_alpha": 0.22,
        "hand_weight": 0.65,
        "click_cooldown": 1.0,
        "dwell_enabled": True,
        "dwell_seconds": 2.0,
        "active_modules": {"hand": True, "eye": True},
    },
}


def _deep_merge(defaults: dict, overrides: dict) -> dict:
    merged = {}
    for key, value in defaults.items():
        if isinstance(value, dict):
            merged[key] = _deep_merge(value, overrides.get(key, {}))
        else:
            merged[key] = overrides.get(key, value)

    for key, value in overrides.items():
        if key not in merged:
            merged[key] = value
    return merged


def load_config(path: str = CONFIG_PATH) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            return _deep_merge(DEFAULT_CONFIG, data)
        except Exception:
            pass
    return _deep_merge(DEFAULT_CONFIG, {})


def apply_profile(cfg: dict, profile_name: str) -> dict:
    preset = PROFILE_PRESETS.get(profile_name)
    if not preset:
        return cfg
    merged = _deep_merge(cfg, preset)
    merged["profile_name"] = profile_name
    return merged


def save_config(cfg: dict, path: str = CONFIG_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
