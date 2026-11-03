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


def test_created_public_room_is_returned_and_listed(database):
    room = database.create_room("developers", "yash")

    assert room["id"]
    assert room["name"] == "developers"
    assert room["created_by"] == "yash"
    assert database.get_room(room["id"]) == room
    assert room in database.list_public_rooms()


def test_private_room_is_not_in_public_directory(database):
    room = database.create_room("private-chat", "yash", is_public=False)

    assert room["is_public"] is False
    assert database.find_room(room["id"])["name"] == "private-chat"
    assert all(item["id"] != room["id"] for item in database.list_public_rooms())


def test_only_room_creator_can_delete_public_rooms(database):
    room = database.create_room("team-chat", "host")
    database.save_message("host", "Room history", room["id"])

    with pytest.raises(ValueError, match="Only the room creator"):
        database.delete_public_room(room["id"], "guest")

    deleted = database.delete_public_room(room["id"], "HOST")
    assert deleted["name"] == "team-chat"
    assert database.get_room(room["id"]) is None
    assert database.get_messages(room["id"]) == []

    with pytest.raises(ValueError, match="General room cannot be deleted"):
        database.delete_public_room("GENERAL", "system")
