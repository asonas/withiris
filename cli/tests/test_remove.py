"""Tests for remove command."""

import argparse
from unittest.mock import patch

from iris_cli.main import cmd_remove


class TestCmdRemove:
    def test_removes_channel_by_query(self, capsys):
        config = {
            "version": 2,
            "channels": [
                {"channel_id": "ch-1", "device_name": "iPhone Production",
                 "endpoint": "https://relay.example.com", "push_token": "pt-1", "pubkey": "pk-1"},
                {"channel_id": "ch-2", "device_name": "iPhone Dev",
                 "endpoint": "https://relay-dev.example.com", "push_token": "pt-2", "pubkey": "pk-2"},
            ],
        }
        args = argparse.Namespace(query="Dev")

        with (
            patch("iris_cli.main.load_config", return_value=config),
            patch("iris_cli.main.save_config") as mock_save,
        ):
            cmd_remove(args)
            mock_save.assert_called_once()
            saved = mock_save.call_args[0][0]
            assert len(saved["channels"]) == 1
            assert saved["channels"][0]["channel_id"] == "ch-1"

        captured = capsys.readouterr()
        assert "Removed" in captured.out

    def test_reports_not_found(self, capsys):
        config = {
            "version": 2,
            "channels": [
                {"channel_id": "ch-1", "device_name": "phone1"},
            ],
        }
        args = argparse.Namespace(query="nonexistent")

        with (
            patch("iris_cli.main.load_config", return_value=config),
            patch("iris_cli.main.save_config") as mock_save,
        ):
            cmd_remove(args)
            mock_save.assert_not_called()

        captured = capsys.readouterr()
        assert "No channel matching" in captured.err
