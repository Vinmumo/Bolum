from app.core.security import decrypt_secret, encrypt_secret, mask_key


def test_encrypt_roundtrip():
    secret = "my-super-secret-api-key-abcdef123456"
    enc = encrypt_secret(secret)
    assert enc != secret  # actually encrypted at rest
    assert decrypt_secret(enc) == secret


def test_mask_key_never_leaks_full():
    key = "abcdef1234567890"
    masked = mask_key(key)
    assert masked.endswith("7890")
    assert key not in masked
    assert mask_key("") == ""
    assert mask_key(None) == ""
