# Iris

Send screenshots from your terminal to your iPhone with end-to-end encryption.

Iris encrypts images on your machine using P-256 ECIES before sending them through a relay server. The relay never sees your images — only your iPhone can decrypt them using its Secure Enclave.

## Install

```
uv tool install withiris
```

Or with pip:

```
pip install withiris
```

## Setup

1. Install the [Iris iOS app](https://apps.apple.com/app/iris/TODO) on your iPhone
2. Run the setup command on your machine:

```
iris setup
```

3. Scan the QR code shown in your terminal with the Iris app

That's it. Your machine and iPhone are now paired.

## Usage

Push an image to your iPhone:

```
iris push screenshot.png
```

With a custom title:

```
iris push screenshot.png --title "Bug on login page"
```

Check pairing status:

```
iris status
```

## How it works

```
Terminal (CLI)  ──encrypt──>  Relay (Cloudflare Workers)  ──notify──>  iPhone (Iris app)
                              Stores encrypted blobs only               Decrypts with Secure Enclave
```

1. `iris push` encrypts the image with the iPhone's public key
2. The encrypted blob is uploaded to the relay server
3. The relay sends a push notification to your iPhone
4. The Iris app downloads and decrypts the image

The relay server only handles encrypted data. It cannot see your images.

## Multiple machines

Each machine needs its own setup. Run `iris setup` on every machine you want to send images from. The iOS app supports multiple paired channels.

## Links

- [GitHub](https://github.com/asonas/iris)
- [iOS App (App Store)](https://apps.apple.com/app/iris/TODO)

## License

MIT
