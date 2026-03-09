# Demo Directory

Always respond in English.

This directory contains the demo landing page for Iris CLI.

## Iris CLI Command Reference

### Installation

```bash
pip install iris-cli
```

### Commands

#### `iris setup`

Pair with the iPhone app.

```bash
# Interactive setup (displays QR code for iPhone to scan)
iris setup

# Force re-setup, overwriting existing config
iris setup --force

# URI-based setup (from QR code displayed by iPhone)
iris setup "iris://pair?endpoint=...&channel_id=...&pull_token=..."
```

- Creates a channel on the relay server
- Displays a QR code in the terminal
- iPhone app scans it and registers its P-256 public key
- Config is saved to `~/.config/iris/config.json`

#### `iris push <image_path>`

Encrypt and send a screenshot to iPhone.

```bash
# Basic send
iris push screenshot.png

# Send with a title
iris push screenshot.png --title "Login page screenshot"
```

- Encrypts the image with P-256 ECIES (ECDH + HKDF-SHA256 + AES-256-GCM)
- Uploads encrypted data to the relay server
- iPhone receives an instant notification via Apple Push Notifications
- Images are automatically deleted after 30 minutes

#### `iris status`

Check pairing status.

```bash
iris status
```

- Displays relay endpoint, channel ID, and device name

### Security

- **E2E Encryption**: The relay server cannot view screenshot contents at all
- **Secure Enclave**: iPhone private keys are managed in the Secure Enclave and never leave the device
- **Auto-delete**: Uploaded images are automatically deleted after 30 minutes

### Use Cases

- **Claude Code**: Review AI-generated UI screenshots on your iPhone
- **Playwright**: Monitor E2E test screenshots in real time
- **Remote Dev Server**: Send GUI application screens from SSH sessions to your iPhone

## Demo Page

`index.html` is a single-page demo site showcasing Iris features. To preview locally:

```bash
npx --yes serve demo/
```

### Taking Screenshots

Use Playwright with a 1180x800 viewport (no `--full-page`). This captures only the first view:

```bash
npx --yes playwright screenshot --viewport-size="1180,800" demo/index.html demo/screenshot.png
```
