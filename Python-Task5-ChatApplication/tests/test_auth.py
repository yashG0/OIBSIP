import pytest

from chat_app.auth import AuthService
from chat_app.database import ChatDatabase


@pytest.fixture
def auth(tmp_path):
    return AuthService(ChatDatabase(tmp_path / "auth-test.db"))


def test_register_and_login(auth):
    auth.register("yash", "a-secure-password")

    assert auth.login("yash", "a-secure-password")


def test_wrong_password_fails(auth):
    auth.register("yash", "a-secure-password")

    assert not auth.login("yash", "incorrect-password")


def test_unknown_user_fails(auth):
    assert not auth.login("unknown", "a-secure-password")


def test_short_password_is_rejected(auth):
    with pytest.raises(ValueError, match="at least 8 characters"):
        auth.register("yash", "short")
