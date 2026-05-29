from app.api.security.auth import hash_password, verify_password


def test_hash_password_round_trip_uses_bcrypt_successfully():
    password = "senha-super-segura"

    hashed_password = hash_password(password)

    assert hashed_password.startswith("$2")
    assert hashed_password != password
    assert verify_password(password, hashed_password) is True


def test_verify_password_returns_false_for_invalid_hash():
    assert verify_password("123456", "hash-invalido") is False
