# Changelog

## 2026-03-10

### Added

- CLI マルチチャンネル対応: 複数のiOSデバイスに画像を送信可能に (`fa1b049`, `8d61ae3`)
  - 設定ファイルを v2 形式 (multi-channel) に拡張。v1 からの自動マイグレーション付き
  - `iris push` が全チャンネルに一括送信。`--channel` オプションで特定チャンネルのみに送信可能
  - `iris setup` が既存設定にチャンネルを追加 (既存チャンネルは維持)。`--force` で新規作成
  - `iris status` が全チャンネルの情報を表示
- `iris remove <query>` コマンド: チャンネルIDプレフィックスまたはデバイス名でチャンネルを削除 (`d2040a8`)
- Relay の APNs トピックを環境変数 `APNS_TOPIC` で設定可能に (`e6e49fc`)
  - dev 環境は `com.asonas.iris.debug`、本番は `com.asonas.iris`
