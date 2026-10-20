import pytest

from chat_app.database import ChatDatabase


@pytest.fixture
def database(tmp_path):
    return ChatDatabase(tmp_path / "test.db")


def test_message_persists(database):
    database.save_message("yash", "Hello!")
    messages = database.get_messages()

    assert len(messages) == 1
    assert messages[0]["username"] == "yash"
    assert messages[0]["content"] == "Hello!"
    assert messages[0]["room"] == "general"
    assert messages[0]["created_at"]


def test_message_history_is_separated_by_room(database):
    database.save_message("yash", "Hello general", "general")
    database.save_message("alex", "Hello devs", "developers")

    assert len(database.get_messages("general")) == 1
    assert database.get_messages("developers")[0]["content"] == "Hello devs"


def test_duplicate_username_is_rejected(database):
    database.create_user("yash", "hash-one")

    with pytest.raises(ValueError, match="already registered"):
        database.create_user("YASH", "hash-two")
