"""Configuration management for Iris CLI."""

import json
from pathlib import Path
from urllib.parse import urlparse, parse_qs

CONFIG_PATH = Path.home() / ".config" / "iris" / "config.json"


def load_config() -> dict:
    """Load config from ~/.config/iris/config.json."""
    if not CONFIG_PATH.exists():
        raise SystemExit(f"Config not found at {CONFIG_PATH}. Run 'iris setup <uri>' first.")
    return json.loads(CONFIG_PATH.read_text())


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
