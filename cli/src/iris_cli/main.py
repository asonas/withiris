"""Iris CLI - E2E encrypted screenshot relay client."""

import argparse
import mimetypes
import sys
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse

import httpx

from .config import CONFIG_PATH, add_channel, find_channel, get_channels, load_config, new_config, parse_pair_uri, remove_channel, save_config
from .crypto import build_payload, encrypt, load_public_key
from .setup import setup_interactive


def cmd_status() -> None:
    print(f"iris v{version('withiris')}")
    if not CONFIG_PATH.exists():
        print("Not configured. Run 'iris setup' to pair with an iOS device.")
        return

    config = load_config()
    channels = get_channels(config)

    if not channels:
        print("Not paired. Run 'iris setup' to add a channel.")
        return

    print(f"{len(channels)} channel(s) configured:")
    for ch in channels:
        endpoint = ch.get("endpoint", "unknown")
        channel_id = ch.get("channel_id", "unknown")
        device_name = ch.get("device_name")
        host = urlparse(endpoint).hostname or endpoint
        print()
        print(f"  relay:      {host}")
        print(f"  channel_id: {channel_id}")
        if device_name:
            print(f"  device:     {device_name}")
def cmd_setup(args: argparse.Namespace) -> None:
    if args.uri:
        channel = parse_pair_uri(args.uri)
        if CONFIG_PATH.exists():
            config = load_config()
        else:
            config = new_config()
        add_channel(config, channel)
        save_config(config)
        print(f"Configuration saved to ~/.config/iris/config.json")
        print(f"  endpoint:   {channel['endpoint']}")
        print(f"  channel_id: {channel['channel_id']}")
    else:
        if CONFIG_PATH.exists() and not args.force:
            existing_config = load_config()
            setup_interactive(endpoint=args.endpoint, existing_config=existing_config)
        else:
            setup_interactive(endpoint=args.endpoint)
def cmd_push(args: argparse.Namespace) -> None:
    config = load_config()
    image_path = Path(args.image)

    if not image_path.exists():
        raise SystemExit(f"File not found: {image_path}")

    image_bytes = image_path.read_bytes()
    content_type = mimetypes.guess_type(str(image_path))[0] or "application/octet-stream"
    title = args.title if args.title else image_path.name

    channel_query = getattr(args, "channel", None)
    if channel_query:
        matched = find_channel(config, channel_query)
        if not matched:
            raise SystemExit(f"No channel matching '{channel_query}'")
        channels = [matched]
    else:
        channels = get_channels(config)

    if not channels:
        raise SystemExit("No channels configured. Run 'iris setup' first.")

    for ch in channels:
        pubkey = load_public_key(ch["pubkey"])
        plaintext = build_payload(image_bytes, title=title, content_type=content_type)
        encrypted = encrypt(plaintext, pubkey)

        url = f"{ch['endpoint']}/channels/{ch['channel_id']}/images"
        response = httpx.post(
            url,
            content=encrypted,
            headers={
                "Authorization": f"Bearer {ch['push_token']}",
                "Content-Type": "application/octet-stream",
            },
        )

        if response.status_code == 201:
            data = response.json()
            print(f"Image pushed successfully: {data['id']}")
        else:
            print(f"Error: {response.status_code} ({ch.get('device_name', ch['channel_id'])})", file=sys.stderr)
            print(response.text, file=sys.stderr)

def cmd_remove(args: argparse.Namespace) -> None:
    config = load_config()
    if remove_channel(config, args.query):
        save_config(config)
        print(f"Removed channel matching '{args.query}'")
    else:
        print(f"No channel matching '{args.query}'", file=sys.stderr)

def main() -> None:
    parser = argparse.ArgumentParser(prog="iris", description="Iris CLI client")
    subparsers = parser.add_subparsers(dest="command")

    # status command
    subparsers.add_parser("status", help="Show pairing status")

    # setup command
    setup_parser = subparsers.add_parser("setup", help="Configure CLI with pairing URI or interactive setup")
    setup_parser.add_argument("uri", nargs="?", default=None, help="iris://pair?... URI (optional, omit for interactive QR setup)")
    setup_parser.add_argument("--force", action="store_true", help="Overwrite existing configuration")
    setup_parser.add_argument("--endpoint", help="Relay endpoint URL (default: https://relay.withiris.dev)")

    # push command
    push_parser = subparsers.add_parser("push", help="Push an image to the relay")
    push_parser.add_argument("image", help="Path to image file")
    push_parser.add_argument("--title", help="Optional title for the image")
    push_parser.add_argument("--channel", help="Send to specific channel (channel_id prefix or device_name)")

    # remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a channel")
    remove_parser.add_argument("query", help="Channel ID prefix or device name to remove")

    args = parser.parse_args()

    if args.command is None or args.command == "status":
        cmd_status()
    elif args.command == "setup":
        cmd_setup(args)
    elif args.command == "push":
        cmd_push(args)
    elif args.command == "remove":
        cmd_remove(args)
if __name__ == "__main__":
    main()
