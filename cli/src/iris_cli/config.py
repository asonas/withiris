"""Configuration management for Iris CLI."""

import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

CONFIG_PATH = Path.home() / ".config" / "iris" / "config.json"


def is_v1_config(config: dict) -> bool:
    """Check if config is v1 format (single channel, flat dict)."""
    return "channel_id" in config and "version" not in config


def migrate_v1_to_v2(config: dict) -> dict:
    """Migrate v1 config (single channel) to v2 format (multi-channel)."""
    channel = {
        "endpoint": config["endpoint"],
        "channel_id": config["channel_id"],
        "push_token": config["push_token"],
        "pubkey": config["pubkey"],
        "device_name": config.get("device_name", "unknown"),
    }
    return {"version": 2, "channels": [channel]}


def new_config() -> dict:
    """Create an empty v2 config."""
    return {"version": 2, "channels": []}


def get_channels(config: dict) -> list[dict]:
    """Get the list of channels from a v2 config."""
    return config["channels"]


def add_channel(config: dict, channel: dict) -> dict:
    """Add a channel to a v2 config."""
    config["channels"].append(channel)
    return config


def find_channel(config: dict, query: str) -> dict | None:
    """Find a channel by channel_id prefix or device_name substring."""
    for ch in config["channels"]:
        if ch["channel_id"].startswith(query):
            return ch
    for ch in config["channels"]:
        if query in ch.get("device_name", ""):
            return ch
    return None


def load_config() -> dict:
    """Load config from ~/.config/iris/config.json. Auto-migrates v1 to v2."""
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Config not found at {CONFIG_PATH}. Run 'iris setup <uri>' first.")
    config = json.loads(CONFIG_PATH.read_text())
    if is_v1_config(config):
        config = migrate_v1_to_v2(config)
        save_config(config)
    return config


def save_config(config: dict) -> None:
    """Save config to ~/.config/iris/config.json."""
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2))


def parse_pair_uri(uri: str) -> dict:
    """Parse iris://pair?endpoint=...&channel_id=...&push_token=...&pubkey=... URI."""
    parsed = urlparse(uri)
    if parsed.scheme != "iris" or parsed.netloc != "pair":
        raise SystemExit(f"Invalid URI scheme. Expected iris://pair?..., got: {uri}")

    params = parse_qs(parsed.query)

    required = ["endpoint", "channel_id", "push_token", "pubkey"]
    for key in required:
        if key not in params:
            raise SystemExit(f"Missing required parameter: {key}")

    return {
        "endpoint": params["endpoint"][0],
        "channel_id": params["channel_id"][0],
        "push_token": params["push_token"][0],
        "pubkey": params["pubkey"][0],
    }
