from app.core.security import generate_token, hash_password, hash_token, verify_password


def test_password_hash_verifies_password() -> None:
    password_hash = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", password_hash)
    assert not verify_password("incorrect", password_hash)


def test_tokens_are_random_and_hashed() -> None:
    first = generate_token()
    second = generate_token()
    assert first != second
    assert hash_token(first) != first
    assert hash_token(first) != hash_token(second)

