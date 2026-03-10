"""Tests for push command - multi-channel support."""

import argparse
from unittest.mock import patch, MagicMock

import httpx

from iris_cli.main import cmd_push


def make_v2_config(*channels):
    return {"version": 2, "channels": list(channels)}


def make_channel(channel_id="ch-1", endpoint="https://relay.example.com",
                 push_token="push-tok", pubkey="base64-pubkey", device_name="phone"):
    return {
        "endpoint": endpoint,
        "channel_id": channel_id,
        "push_token": push_token,
        "pubkey": pubkey,
        "device_name": device_name,
    }


class TestCmdPushMultiChannel:
    def test_sends_to_all_channels(self, tmp_path):
        image = tmp_path / "test.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        args = argparse.Namespace(image=str(image), title=None, channel=None)

        config = make_v2_config(
            make_channel(channel_id="ch-1"),
            make_channel(channel_id="ch-2"),
        )

        success_response = httpx.Response(201, json={"id": "img-1"})

        with (
            patch("iris_cli.main.load_config", return_value=config),
            patch("iris_cli.main.encrypt", return_value=b"encrypted"),
            patch("iris_cli.main.load_public_key", return_value=MagicMock()),
            patch("iris_cli.main.build_payload", return_value=b"payload"),
            patch("iris_cli.main.httpx.post", return_value=success_response) as mock_post,
        ):
            cmd_push(args)
            assert mock_post.call_count == 2

    def test_sends_to_specific_channel(self, tmp_path):
        image = tmp_path / "test.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        args = argparse.Namespace(image=str(image), title=None, channel="ch-2")

        config = make_v2_config(
            make_channel(channel_id="ch-1"),
            make_channel(channel_id="ch-2", endpoint="https://relay-dev.example.com"),
        )

        success_response = httpx.Response(201, json={"id": "img-1"})

        with (
            patch("iris_cli.main.load_config", return_value=config),
            patch("iris_cli.main.encrypt", return_value=b"encrypted"),
            patch("iris_cli.main.load_public_key", return_value=MagicMock()),
            patch("iris_cli.main.build_payload", return_value=b"payload"),
            patch("iris_cli.main.httpx.post", return_value=success_response) as mock_post,
        ):
            cmd_push(args)
            assert mock_post.call_count == 1
            url = mock_post.call_args[0][0]
            assert "relay-dev.example.com" in url

    def test_continues_on_partial_failure(self, tmp_path, capsys):
        image = tmp_path / "test.png"
        image.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        args = argparse.Namespace(image=str(image), title=None, channel=None)

        config = make_v2_config(
            make_channel(channel_id="ch-1"),
            make_channel(channel_id="ch-2"),
        )

        fail_response = httpx.Response(500, text="Internal error")
        success_response = httpx.Response(201, json={"id": "img-2"})

        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return fail_response if call_count == 1 else success_response

        with (
            patch("iris_cli.main.load_config", return_value=config),
            patch("iris_cli.main.encrypt", return_value=b"encrypted"),
            patch("iris_cli.main.load_public_key", return_value=MagicMock()),
            patch("iris_cli.main.build_payload", return_value=b"payload"),
            patch("iris_cli.main.httpx.post", side_effect=mock_post),
        ):
            cmd_push(args)
            assert call_count == 2

        captured = capsys.readouterr()
        assert "Error" in captured.err
        assert "img-2" in captured.out
