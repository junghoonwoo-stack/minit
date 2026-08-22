import json

import pytest
from cryptography.exceptions import InvalidTag

from minit.crypto import decrypt_envelope, encrypt_envelope, generate_key


def test_envelope_round_trip_and_contains_no_plaintext():
    wrapping_key = generate_key()
    plaintext = b"super-secret-value"
    envelope = encrypt_envelope(
        plaintext,
        wrapping_key,
        context={"type": "test", "app_id": "app-1"},
    )

    serialized = json.dumps(envelope)
    assert "super-secret-value" not in serialized
    assert decrypt_envelope(envelope, wrapping_key) == plaintext


def test_wrong_wrapping_key_cannot_decrypt():
    envelope = encrypt_envelope(
        b"secret",
        generate_key(),
        context={"type": "test", "app_id": "app-1"},
    )

    with pytest.raises(InvalidTag):
        decrypt_envelope(envelope, generate_key())


def test_ciphertext_tampering_is_detected():
    wrapping_key = generate_key()
    envelope = encrypt_envelope(
        b"secret",
        wrapping_key,
        context={"type": "test", "app_id": "app-1"},
    )
    envelope["ciphertext"] = envelope["ciphertext"][:-2] + "AA"

    with pytest.raises(Exception):
        decrypt_envelope(envelope, wrapping_key)


def test_context_is_authenticated():
    wrapping_key = generate_key()
    envelope = encrypt_envelope(
        b"secret",
        wrapping_key,
        context={"type": "app-secret", "app_id": "app-1", "name": "TOKEN"},
    )
    envelope["context"]["app_id"] = "app-2"

    with pytest.raises(InvalidTag):
        decrypt_envelope(envelope, wrapping_key)
