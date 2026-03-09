"""Iris CLI - E2E encrypted screenshot relay client."""

import argparse
import mimetypes
import sys
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import CONFIG_PATH, load_config, parse_pair_uri, save_config
from .crypto import build_payload, encrypt, load_public_key
from .setup import setup_interactive


def cmd_status() -> None:
    print(f"iris v{version('withiris')}")
    if not CONFIG_PATH.exists():
        print("Not configured. Run 'iris setup' to pair with an iOS device.")
        return

    config = load_config()
    endpoint = config.get("endpoint", "unknown")
    channel_id = config.get("channel_id", "unknown")
    device_name = config.get("device_name")
    host = urlparse(endpoint).hostname or endpoint
    print(f"Paired")
    print(f"  relay:      {host}")
    print(f"  channel_id: {channel_id}")
    if device_name:
        print(f"  device:     {device_name}")
def cmd_setup(args: argparse.Namespace) -> None:
    if args.uri:
        config = parse_pair_uri(args.uri)
        save_config(config)
        print(f"Configuration saved to ~/.config/iris/config.json")
        print(f"  endpoint:   {config['endpoint']}")
        print(f"  channel_id: {config['channel_id']}")
    else:
        if CONFIG_PATH.exists() and not args.force:
            print("Configuration already exists. Use 'iris setup --force' to overwrite.", file=sys.stderr)
            raise SystemExit(1)
        setup_interactive()
def cmd_push(args: argparse.Namespace) -> None:
    config = load_config()
    image_path = Path(args.image)

    if not image_path.exists():
        raise SystemExit(f"File not found: {image_path}")

    image_bytes = image_path.read_bytes()
    content_type = mimetypes.guess_type(str(image_path))[0] or "application/octet-stream"
    title = args.title if args.title else image_path.name

    # Build and encrypt payload
    pubkey = load_public_key(config["pubkey"])
    plaintext = build_payload(image_bytes, title=title, content_type=content_type)
    encrypted = encrypt(plaintext, pubkey)

    # POST to relay
    url = f"{config['endpoint']}/channels/{config['channel_id']}/images"
    response = httpx.post(
        url,
        content=encrypted,
        headers={
            "Authorization": f"Bearer {config['push_token']}",
            "Content-Type": "application/octet-stream",
        },
    )

    if response.status_code == 201:
        data = response.json()
        print(f"Image pushed successfully: {data['id']}")
    else:
        print(f"Error: {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        raise SystemExit(1)
def main() -> None:
    parser = argparse.ArgumentParser(prog="iris", description="Iris CLI client")
    subparsers = parser.add_subparsers(dest="command")

    # status command
    subparsers.add_parser("status", help="Show pairing status")

    # setup command
    setup_parser = subparsers.add_parser("setup", help="Configure CLI with pairing URI or interactive setup")
    setup_parser.add_argument("uri", nargs="?", default=None, help="iris://pair?... URI (optional, omit for interactive QR setup)")
    setup_parser.add_argument("--force", action="store_true", help="Overwrite existing configuration")

    # push command
    push_parser = subparsers.add_parser("push", help="Push an image to the relay")
    push_parser.add_argument("image", help="Path to image file")
    push_parser.add_argument("--title", help="Optional title for the image")

    args = parser.parse_args()

    if args.command is None or args.command == "status":
        cmd_status()
    elif args.command == "setup":
        cmd_setup(args)
    elif args.command == "push":
        cmd_push(args)
if __name__ == "__main__":
    main()
