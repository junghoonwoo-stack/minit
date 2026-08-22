from __future__ import annotations

import base64
import json
import os
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ENVELOPE_VERSION = 1
ALGORITHM = "AES-256-GCM"
KEY_BYTES = 32
NONCE_BYTES = 12


def generate_key() -> bytes:
    return AESGCM.generate_key(bit_length=256)


def _require_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) != KEY_BYTES:
        raise ValueError("Minit encryption keys must be 32 bytes")


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _aad(context: dict[str, str]) -> bytes:
    payload = {
        "algorithm": ALGORITHM,
        "context": context,
        "version": ENVELOPE_VERSION,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def encrypt_envelope(
    plaintext: bytes,
    wrapping_key: bytes,
    *,
    context: dict[str, str],
) -> dict[str, Any]:
    """Encrypt bytes using a fresh per-object data key and authenticated envelope.

    The wrapping key is never serialized into the returned object. A fresh random
    data key and nonces are generated for every envelope.
    """
    _require_key(wrapping_key)
    if not isinstance(plaintext, bytes):
        raise TypeError("plaintext must be bytes")

    aad = _aad(context)
    data_key = generate_key()
    data_nonce = os.urandom(NONCE_BYTES)
    wrapped_key_nonce = os.urandom(NONCE_BYTES)

    ciphertext = AESGCM(data_key).encrypt(data_nonce, plaintext, aad)
    wrapped_key = AESGCM(wrapping_key).encrypt(
        wrapped_key_nonce,
        data_key,
        aad + b"|wrapped-key",
    )

    return {
        "version": ENVELOPE_VERSION,
        "algorithm": ALGORITHM,
        "context": dict(context),
        "data_nonce": _b64encode(data_nonce),
        "wrapped_key_nonce": _b64encode(wrapped_key_nonce),
        "wrapped_key": _b64encode(wrapped_key),
        "ciphertext": _b64encode(ciphertext),
    }


def decrypt_envelope(envelope: dict[str, Any], wrapping_key: bytes) -> bytes:
    _require_key(wrapping_key)
    if envelope.get("version") != ENVELOPE_VERSION:
        raise ValueError("Unsupported encrypted-envelope version")
    if envelope.get("algorithm") != ALGORITHM:
        raise ValueError("Unsupported encrypted-envelope algorithm")

    context = envelope.get("context")
    if not isinstance(context, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in context.items()
    ):
        raise ValueError("Invalid encrypted-envelope context")

    aad = _aad(context)
    wrapped_key = _b64decode(envelope["wrapped_key"])
    wrapped_key_nonce = _b64decode(envelope["wrapped_key_nonce"])
    data_key = AESGCM(wrapping_key).decrypt(
        wrapped_key_nonce,
        wrapped_key,
        aad + b"|wrapped-key",
    )
    _require_key(data_key)

    return AESGCM(data_key).decrypt(
        _b64decode(envelope["data_nonce"]),
        _b64decode(envelope["ciphertext"]),
        aad,
    )
