from unittest.mock import patch, call

from iris_cli.main import cmd_status, main


class TestCmdStatus:
    def test_shows_version(self, capsys):
        with patch("iris_cli.main.CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            cmd_status()

        captured = capsys.readouterr()
        assert "iris v" in captured.out

    def test_shows_not_configured_when_config_missing(self, capsys):
        with patch("iris_cli.main.CONFIG_PATH") as mock_path:
            mock_path.exists.return_value = False
            cmd_status()

        captured = capsys.readouterr()
        assert "Not configured" in captured.out

    def test_shows_paired_status_when_configured(self, capsys):
        config = {
            "version": 2,
            "channels": [
                {
                    "endpoint": "https://relay.example.com",
                    "channel_id": "ch-abc123",
                    "push_token": "push-tok",
                    "pubkey": "base64-pubkey-data",
                }
            ],
        }
        with (
            patch("iris_cli.main.CONFIG_PATH") as mock_path,
            patch("iris_cli.main.load_config", return_value=config),
        ):
            mock_path.exists.return_value = True
            cmd_status()

        captured = capsys.readouterr()
        assert "ch-abc123" in captured.out
        assert "relay.example.com" in captured.out

    def test_shows_device_name_when_configured(self, capsys):
        config = {
            "version": 2,
            "channels": [
                {
                    "endpoint": "https://relay.example.com",
                    "channel_id": "ch-abc123",
                    "push_token": "push-tok",
                    "pubkey": "base64-pubkey-data",
                    "device_name": "my-laptop",
                }
            ],
        }
        with (
            patch("iris_cli.main.CONFIG_PATH") as mock_path,
            patch("iris_cli.main.load_config", return_value=config),
        ):
            mock_path.exists.return_value = True
            cmd_status()

        captured = capsys.readouterr()
        assert "my-laptop" in captured.out

    def test_shows_multiple_channels(self, capsys):
        config = {
            "version": 2,
            "channels": [
                {
                    "endpoint": "https://relay.example.com",
                    "channel_id": "ch-1",
                    "push_token": "push-tok-1",
                    "pubkey": "pk-1",
                    "device_name": "iPhone Production",
                },
                {
                    "endpoint": "https://relay-dev.example.com",
                    "channel_id": "ch-2",
                    "push_token": "push-tok-2",
                    "pubkey": "pk-2",
                    "device_name": "iPhone Dev",
                },
            ],
        }
        with (
            patch("iris_cli.main.CONFIG_PATH") as mock_path,
            patch("iris_cli.main.load_config", return_value=config),
        ):
            mock_path.exists.return_value = True
            cmd_status()

        captured = capsys.readouterr()
        assert "iPhone Production" in captured.out
        assert "iPhone Dev" in captured.out
        assert "ch-1" in captured.out
        assert "ch-2" in captured.out

    def test_shows_no_channels_when_empty(self, capsys):
        config = {"version": 2, "channels": []}
        with (
            patch("iris_cli.main.CONFIG_PATH") as mock_path,
            patch("iris_cli.main.load_config", return_value=config),
        ):
            mock_path.exists.return_value = True
            cmd_status()

        captured = capsys.readouterr()
        assert "Not paired" in captured.out

    def test_status_subcommand_calls_cmd_status(self):
        with (
            patch("iris_cli.main.cmd_status") as mock_cmd_status,
            patch("sys.argv", ["iris", "status"]),
        ):
            main()
            mock_cmd_status.assert_called_once()

    def test_no_args_defaults_to_status(self):
        with (
            patch("iris_cli.main.cmd_status") as mock_cmd_status,
            patch("sys.argv", ["iris"]),
        ):
            main()
            mock_cmd_status.assert_called_once()
