"""Interactive setup for CLI-initiated pairing."""

import socket
import sys
import time
from urllib.parse import urlencode

import httpx
import qrcode

from .config import save_config

ENDPOINT = "https://relay.withiris.dev"
DEFAULT_POLL_INTERVAL = 2
DEFAULT_POLL_TIMEOUT = 300


def build_pair_uri(endpoint: str, channel_id: str, pull_token: str, device_name: str | None = None) -> str:
    """Build an iris://pair URI for QR code display."""
    params = {
        "endpoint": endpoint,
        "channel_id": channel_id,
        "pull_token": pull_token,
    }
    if device_name:
        params["device_name"] = device_name
    return f"iris://pair?{urlencode(params)}"


def display_qr(uri: str) -> None:
    """Display QR code in terminal using Unicode half-block characters."""
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        border=1,
    )
    qr.add_data(uri)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    rows = len(matrix)

    for r in range(0, rows, 2):
        line = []
        for c in range(len(matrix[0])):
            top = matrix[r][c]
            bottom = matrix[r + 1][c] if r + 1 < rows else False
            if top and bottom:
                line.append("\u2588")  # full block
            elif top:
                line.append("\u2580")  # upper half block
            elif bottom:
                line.append("\u2584")  # lower half block
            else:
                line.append(" ")
        print("".join(line))
    print()


def poll_for_pubkey(
    endpoint: str,
    channel_id: str,
    push_token: str,
    poll_interval: float = DEFAULT_POLL_INTERVAL,
    timeout: float = DEFAULT_POLL_TIMEOUT,
) -> str:
    """Poll relay for pubkey until iOS registers it or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = httpx.get(
            f"{endpoint}/channels/{channel_id}/pubkey",
            headers={"Authorization": f"Bearer {push_token}"},
        )
        if response.status_code == 200:
            data = response.json()
            if "pubkey" in data:
                return data["pubkey"]
        elif response.status_code != 202:
            raise SystemExit(f"Unexpected response: {response.status_code}")
        time.sleep(poll_interval)
    raise SystemExit("Pairing timed out. Please try again.")


def setup_interactive() -> None:
    """Create channel, display QR, poll for pubkey, save config."""
    endpoint = ENDPOINT
    device_name = socket.gethostname()
    response = httpx.post(f"{endpoint}/channels", json={"device_name": device_name})
    if response.status_code != 201:
        raise SystemExit(f"Failed to create channel: {response.status_code} {response.text}")

    data = response.json()
    channel_id = data["channel_id"]
    push_token = data["push_token"]
    pull_token = data["pull_token"]

    uri = build_pair_uri(endpoint, channel_id, pull_token, device_name=device_name)

    print("Scan this QR code with the Iris iOS app:")
    print()
    display_qr(uri)
    print()
    print(f"Or manually enter: {uri}")
    print()

    print("Waiting for iOS to complete pairing...", end="", flush=True)
    pubkey = poll_for_pubkey(endpoint, channel_id, push_token)
    print(" Done!")

    config = {
        "endpoint": endpoint,
        "channel_id": channel_id,
        "push_token": push_token,
        "pubkey": pubkey,
        "device_name": device_name,
    }
    save_config(config)
    print(f"Configuration saved to ~/.config/iris/config.json")
