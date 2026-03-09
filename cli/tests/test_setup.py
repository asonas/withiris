import argparse
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs

import httpx
import pytest

from iris_cli.main import cmd_setup
from iris_cli.setup import build_pair_uri, display_qr, poll_for_pubkey, setup_interactive


class TestBuildPairUri:
    def test_generates_valid_iris_uri(self):
        uri = build_pair_uri(
            endpoint="https://relay.example.com",
            channel_id="test-channel-123",
            pull_token="pull-token-abc",
        )

        parsed = urlparse(uri)
        assert parsed.scheme == "iris"
        assert parsed.netloc == "pair"

    def test_includes_all_parameters(self):
        uri = build_pair_uri(
            endpoint="https://relay.example.com",
            channel_id="test-channel-123",
            pull_token="pull-token-abc",
        )

        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        assert params["endpoint"] == ["https://relay.example.com"]
        assert params["channel_id"] == ["test-channel-123"]
        assert params["pull_token"] == ["pull-token-abc"]

    def test_does_not_include_push_token_or_pubkey(self):
        uri = build_pair_uri(
            endpoint="https://relay.example.com",
            channel_id="ch-1",
            pull_token="pt-1",
        )

        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        assert "push_token" not in params
        assert "pubkey" not in params

    def test_includes_device_name_when_provided(self):
        uri = build_pair_uri(
            endpoint="https://relay.example.com",
            channel_id="ch-1",
            pull_token="pt-1",
            device_name="my-laptop",
        )

        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        assert params["device_name"] == ["my-laptop"]

    def test_omits_device_name_when_none(self):
        uri = build_pair_uri(
            endpoint="https://relay.example.com",
            channel_id="ch-1",
            pull_token="pt-1",
        )

        parsed = urlparse(uri)
        params = parse_qs(parsed.query)
        assert "device_name" not in params


class TestPollForPubkey:
    def test_returns_pubkey_on_200(self):
        response = httpx.Response(200, json={"pubkey": "test-pubkey-base64"})
        with patch("iris_cli.setup.httpx.get", return_value=response):
            result = poll_for_pubkey(
                "https://relay.example.com", "ch-1", "push-token-1",
                poll_interval=0, timeout=5,
            )
        assert result == "test-pubkey-base64"

    def test_retries_on_202_then_succeeds(self):
        pending = httpx.Response(200, json={"status": "pending"})
        pending._status_code = 202
        ready = httpx.Response(200, json={"pubkey": "found-pubkey"})

        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return pending if call_count <= 2 else ready

        with patch("iris_cli.setup.httpx.get", side_effect=mock_get):
            result = poll_for_pubkey(
                "https://relay.example.com", "ch-1", "push-token-1",
                poll_interval=0, timeout=5,
            )
        assert result == "found-pubkey"
        assert call_count == 3

    def test_raises_on_timeout(self):
        pending = httpx.Response(202, json={"status": "pending"})
        with patch("iris_cli.setup.httpx.get", return_value=pending):
            with pytest.raises(SystemExit):
                poll_for_pubkey(
                    "https://relay.example.com", "ch-1", "push-token-1",
                    poll_interval=0, timeout=0,
                )

    def test_sends_correct_auth_header(self):
        response = httpx.Response(200, json={"pubkey": "pk"})

        def mock_get(url, headers=None):
            assert headers["Authorization"] == "Bearer my-push-token"
            return response

        with patch("iris_cli.setup.httpx.get", side_effect=mock_get):
            poll_for_pubkey(
                "https://relay.example.com", "ch-1", "my-push-token",
                poll_interval=0, timeout=5,
            )


class TestSetupInteractive:
    def test_creates_channel_shows_qr_and_saves_config(self):
        create_response = httpx.Response(201, json={
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pull_token": "pull-tok",
        })

        with (
            patch("iris_cli.setup.httpx.post", return_value=create_response) as mock_post,
            patch("iris_cli.setup.poll_for_pubkey", return_value="test-pubkey"),
            patch("iris_cli.setup.save_config") as mock_save,
            patch("iris_cli.setup.display_qr"),
        ):
            setup_interactive()

            mock_post.assert_called_once()
            assert "/channels" in mock_post.call_args[0][0]
            mock_save.assert_called_once()
            config = mock_save.call_args[0][0]
            assert config["channel_id"] == "ch-123"
            assert config["push_token"] == "push-tok"
            assert config["pubkey"] == "test-pubkey"

    def test_sends_device_name_to_relay(self):
        create_response = httpx.Response(201, json={
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pull_token": "pull-tok",
        })

        with (
            patch("iris_cli.setup.httpx.post", return_value=create_response) as mock_post,
            patch("iris_cli.setup.poll_for_pubkey", return_value="test-pubkey"),
            patch("iris_cli.setup.save_config"),
            patch("iris_cli.setup.display_qr"),
            patch("iris_cli.setup.socket.gethostname", return_value="my-laptop"),
        ):
            setup_interactive()

            # Verify device_name is sent in POST body
            call_kwargs = mock_post.call_args
            assert call_kwargs[1]["json"]["device_name"] == "my-laptop"

    def test_includes_device_name_in_qr_uri(self):
        create_response = httpx.Response(201, json={
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pull_token": "pull-tok",
        })

        with (
            patch("iris_cli.setup.httpx.post", return_value=create_response),
            patch("iris_cli.setup.poll_for_pubkey", return_value="test-pubkey"),
            patch("iris_cli.setup.save_config"),
            patch("iris_cli.setup.display_qr") as mock_qr,
            patch("iris_cli.setup.socket.gethostname", return_value="my-laptop"),
        ):
            setup_interactive()

            uri = mock_qr.call_args[0][0]
            assert "device_name=my-laptop" in uri

    def test_saves_device_name_in_config(self):
        create_response = httpx.Response(201, json={
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pull_token": "pull-tok",
        })

        with (
            patch("iris_cli.setup.httpx.post", return_value=create_response),
            patch("iris_cli.setup.poll_for_pubkey", return_value="test-pubkey"),
            patch("iris_cli.setup.save_config") as mock_save,
            patch("iris_cli.setup.display_qr"),
            patch("iris_cli.setup.socket.gethostname", return_value="my-laptop"),
        ):
            setup_interactive()

            config = mock_save.call_args[0][0]
            assert config["device_name"] == "my-laptop"

    def test_raises_on_channel_creation_failure(self):
        error_response = httpx.Response(500, json={"detail": "Internal error"})

        with (
            patch("iris_cli.setup.httpx.post", return_value=error_response),
        ):
            with pytest.raises(SystemExit):
                setup_interactive()


class TestCmdSetup:
    def test_with_uri_uses_legacy_flow(self):
        args = argparse.Namespace(
            uri="iris://pair?endpoint=https%3A%2F%2Frelay.example.com&channel_id=ch-1&push_token=pt-1&pubkey=pk-1",
            force=False,
        )
        with patch("iris_cli.main.save_config") as mock_save:
            cmd_setup(args)
            mock_save.assert_called_once()
            config = mock_save.call_args[0][0]
            assert config["endpoint"] == "https://relay.example.com"
            assert config["pubkey"] == "pk-1"

    def test_without_uri_uses_interactive_flow(self):
        args = argparse.Namespace(uri=None, force=False)
        with (
            patch("iris_cli.main.CONFIG_PATH") as mock_path,
            patch("iris_cli.main.setup_interactive") as mock_interactive,
        ):
            mock_path.exists.return_value = False
            cmd_setup(args)
            mock_interactive.assert_called_once_with()

    def test_warns_when_config_exists_without_force(self, capsys):
        args = argparse.Namespace(uri=None, force=False)
        with (
            patch("iris_cli.main.CONFIG_PATH") as mock_path,
            patch("iris_cli.main.setup_interactive"),
        ):
            mock_path.exists.return_value = True
            with pytest.raises(SystemExit):
                cmd_setup(args)

        captured = capsys.readouterr()
        assert "--force" in captured.err

    def test_proceeds_with_force_when_config_exists(self):
        args = argparse.Namespace(uri=None, force=True)
        with (
            patch("iris_cli.main.CONFIG_PATH") as mock_path,
            patch("iris_cli.main.setup_interactive") as mock_interactive,
        ):
            mock_path.exists.return_value = True
            cmd_setup(args)
            mock_interactive.assert_called_once_with()


class TestDisplayQr:
    def test_uses_unicode_half_block_characters(self, capsys):
        display_qr("https://example.com")
        captured = capsys.readouterr()
        assert "\u2584" in captured.out or "\u2580" in captured.out or "\u2588" in captured.out

    def test_output_is_compact(self, capsys):
        display_qr("https://example.com")
        captured = capsys.readouterr()
        lines = captured.out.strip().split("\n")
        # Half-block rendering should produce fewer lines than full-block
        assert len(lines) < 25
