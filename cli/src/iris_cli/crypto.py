"""P-256 ECIES encryption for Iris wire format."""

import os
import base64
import json

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

WIRE_VERSION = 0x01
HKDF_INFO = b"iris-ecies-v1"


def load_public_key(pubkey_b64: str) -> ec.EllipticCurvePublicKey:
    """Load a P-256 public key from base64-encoded uncompressed form."""
    pubkey_bytes = base64.b64decode(pubkey_b64)
    return ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), pubkey_bytes)


def encrypt(plaintext: bytes, receiver_pubkey: ec.EllipticCurvePublicKey) -> bytes:
    """Encrypt plaintext using P-256 ECIES.

    Returns wire format: [version(1)] [ephemeral_pubkey(65)] [nonce(12)] [ciphertext+tag]
    """
    # Generate ephemeral key pair
    ephemeral_private = ec.generate_private_key(ec.SECP256R1())
    ephemeral_public = ephemeral_private.public_key()

    # ECDH shared secret
    shared_key = ephemeral_private.exchange(ec.ECDH(), receiver_pubkey)

    # HKDF to derive AES-256 key
    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=HKDF_INFO,
    ).derive(shared_key)

    # AES-256-GCM encryption
    nonce = os.urandom(12)
    aesgcm = AESGCM(derived_key)
    ciphertext_and_tag = aesgcm.encrypt(nonce, plaintext, None)

    # Ephemeral public key in uncompressed form (65 bytes)
    ephemeral_pubkey_bytes = ephemeral_public.public_bytes(
        serialization.Encoding.X962,
        serialization.PublicFormat.UncompressedPoint,
    )

    # Wire format
    return bytes([WIRE_VERSION]) + ephemeral_pubkey_bytes + nonce + ciphertext_and_tag


def build_payload(image_bytes: bytes, title: str | None = None, content_type: str = "image/png") -> bytes:
    """Build the plaintext JSON payload to be encrypted."""
    payload: dict = {
        "image": base64.b64encode(image_bytes).decode("ascii"),
        "metadata": {
            "content_type": content_type,
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        },
    }
    if title:
        payload["metadata"]["title"] = title
    return json.dumps(payload, separators=(",", ":")).encode("utf-8")
