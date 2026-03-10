"""Tests for config module - multi-channel support."""

import json
from unittest.mock import patch

from iris_cli.config import (
    add_channel,
    find_channel,
    get_channels,
    is_v1_config,
    load_config,
    migrate_v1_to_v2,
    new_config,
    remove_channel,
)


class TestIsV1Config:
    def test_v1_config_returns_true(self):
        config = {
            "endpoint": "https://relay.example.com",
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pubkey": "base64-pubkey",
        }
        assert is_v1_config(config) is True

    def test_v2_config_returns_false(self):
        config = {
            "version": 2,
            "channels": [
                {
                    "endpoint": "https://relay.example.com",
                    "channel_id": "ch-123",
                    "push_token": "push-tok",
                    "pubkey": "base64-pubkey",
                }
            ],
        }
        assert is_v1_config(config) is False


class TestMigrateV1ToV2:
    def test_converts_v1_to_v2(self):
        v1 = {
            "endpoint": "https://relay.example.com",
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pubkey": "base64-pubkey",
            "device_name": "my-laptop",
        }
        v2 = migrate_v1_to_v2(v1)
        assert v2["version"] == 2
        assert len(v2["channels"]) == 1
        channel = v2["channels"][0]
        assert channel["endpoint"] == "https://relay.example.com"
        assert channel["channel_id"] == "ch-123"
        assert channel["push_token"] == "push-tok"
        assert channel["pubkey"] == "base64-pubkey"
        assert channel["device_name"] == "my-laptop"

    def test_handles_missing_device_name(self):
        v1 = {
            "endpoint": "https://relay.example.com",
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pubkey": "base64-pubkey",
        }
        v2 = migrate_v1_to_v2(v1)
        assert v2["channels"][0]["device_name"] == "unknown"


class TestLoadConfigMigration:
    def test_auto_migrates_v1_to_v2(self, tmp_path):
        v1 = {
            "endpoint": "https://relay.example.com",
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pubkey": "base64-pubkey",
            "device_name": "my-laptop",
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(v1))

        with patch("iris_cli.config.CONFIG_PATH", config_file):
            result = load_config()

        assert result["version"] == 2
        assert len(result["channels"]) == 1
        assert result["channels"][0]["channel_id"] == "ch-123"
        # Verify file was rewritten
        saved = json.loads(config_file.read_text())
        assert saved["version"] == 2

    def test_returns_v2_as_is(self, tmp_path):
        v2 = {
            "version": 2,
            "channels": [
                {
                    "endpoint": "https://relay.example.com",
                    "channel_id": "ch-123",
                    "push_token": "push-tok",
                    "pubkey": "base64-pubkey",
                    "device_name": "my-laptop",
                }
            ],
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(v2))

        with patch("iris_cli.config.CONFIG_PATH", config_file):
            result = load_config()

        assert result["version"] == 2
        assert result["channels"][0]["channel_id"] == "ch-123"


class TestNewConfig:
    def test_creates_empty_v2_config(self):
        config = new_config()
        assert config["version"] == 2
        assert config["channels"] == []


class TestGetChannels:
    def test_returns_channels_list(self):
        config = {
            "version": 2,
            "channels": [
                {"channel_id": "ch-1", "device_name": "phone1"},
                {"channel_id": "ch-2", "device_name": "phone2"},
            ],
        }
        channels = get_channels(config)
        assert len(channels) == 2
        assert channels[0]["channel_id"] == "ch-1"
        assert channels[1]["channel_id"] == "ch-2"


class TestAddChannel:
    def test_adds_channel_to_existing_config(self):
        config = new_config()
        channel = {
            "endpoint": "https://relay.example.com",
            "channel_id": "ch-123",
            "push_token": "push-tok",
            "pubkey": "base64-pubkey",
            "device_name": "my-phone",
        }
        updated = add_channel(config, channel)
        assert len(updated["channels"]) == 1
        assert updated["channels"][0]["channel_id"] == "ch-123"

    def test_appends_to_existing_channels(self):
        config = {
            "version": 2,
            "channels": [
                {"channel_id": "ch-1", "device_name": "phone1"},
            ],
        }
        channel = {"channel_id": "ch-2", "device_name": "phone2"}
        updated = add_channel(config, channel)
        assert len(updated["channels"]) == 2
        assert updated["channels"][1]["channel_id"] == "ch-2"


class TestFindChannel:
    def setup_method(self):
        self.config = {
            "version": 2,
            "channels": [
                {"channel_id": "abc-123-def", "device_name": "iPhone Production"},
                {"channel_id": "xyz-789-ghi", "device_name": "iPhone Dev"},
            ],
        }

    def test_finds_by_channel_id_prefix(self):
        result = find_channel(self.config, "abc")
        assert result["channel_id"] == "abc-123-def"

    def test_finds_by_device_name_substring(self):
        result = find_channel(self.config, "Dev")
        assert result["channel_id"] == "xyz-789-ghi"

    def test_returns_none_when_not_found(self):
        result = find_channel(self.config, "nonexistent")
        assert result is None

    def test_finds_by_exact_channel_id(self):
        result = find_channel(self.config, "abc-123-def")
        assert result["channel_id"] == "abc-123-def"


class TestRemoveChannel:
    def test_removes_by_channel_id(self):
        config = {
            "version": 2,
            "channels": [
                {"channel_id": "ch-1", "device_name": "phone1"},
                {"channel_id": "ch-2", "device_name": "phone2"},
            ],
        }
        removed = remove_channel(config, "ch-1")
        assert removed is True
        assert len(config["channels"]) == 1
        assert config["channels"][0]["channel_id"] == "ch-2"

    def test_removes_by_device_name(self):
        config = {
            "version": 2,
            "channels": [
                {"channel_id": "ch-1", "device_name": "iPhone Production"},
                {"channel_id": "ch-2", "device_name": "iPhone Dev"},
            ],
        }
        removed = remove_channel(config, "Dev")
        assert removed is True
        assert len(config["channels"]) == 1
        assert config["channels"][0]["channel_id"] == "ch-1"

    def test_returns_false_when_not_found(self):
        config = {
            "version": 2,
            "channels": [
                {"channel_id": "ch-1", "device_name": "phone1"},
            ],
        }
        removed = remove_channel(config, "nonexistent")
        assert removed is False
        assert len(config["channels"]) == 1
