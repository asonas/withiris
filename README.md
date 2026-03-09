# Iris

E2E encrypted screenshot delivery from remote servers to your iPhone.

Screenshots captured by AI agents (Claude Code) or automated tests (Playwright) on remote servers are encrypted with P-256 ECIES and delivered to your iPhone via push notification. The relay server holds only ciphertext and cannot view image contents.

## Architecture

```
CLI (sender) ──> Relay (Cloudflare Workers) ──> iOS App (receiver)
  encrypts          stores ciphertext           decrypts via
  with public key   (no decryption key)         Secure Enclave
```

## Getting Started

### 1. Install the iOS App

Download Iris from the App Store. Requires iOS 26.0 or later.

### 2. Install the CLI

```bash
pip install withiris
```

Requires Python 3.11 or later.

### 3. Pair

```bash
iris setup
```

Scan the displayed QR code with the iOS app. Key exchange happens automatically.

### 4. Send

```bash
iris push screenshot.png
```

The image is encrypted and delivered to your iPhone via push notification.

## Components

| Directory | Description |
|-----------|-------------|
| `cli/` | Python CLI client for sending screenshots |
| `relay/` | Cloudflare Workers relay server |
| `pages/` | Landing page and privacy policy |

## Encryption

- **Algorithm**: P-256 ECIES (ECDH + HKDF-SHA256 + AES-256-GCM)
- **Private key**: Stored in iPhone's Secure Enclave, never exported
- **Relay**: Holds only ciphertext, no decryption capability
- **Image TTL**: 30 minutes on relay, then auto-deleted

## Development

### Relay

```bash
cd relay
npm install
npm test
npm run dev    # local dev server
```

### CLI

```bash
cd cli
uv sync
uv run pytest
```

## License

MIT
