import json
from unittest.mock import patch

from assistant import commands
from assistant.commands import handle_command


def test_empty_command():
    response, should_continue = handle_command("")

    assert "didn't catch" in response
    assert should_continue is True


def test_exit_command():
    response, should_continue = handle_command("quit")

    assert response == "Goodbye!"
    assert should_continue is False


def test_time_command():
    response, should_continue = handle_command("what time is it?")

    assert "current time" in response
    assert should_continue is True


def test_date_command():
    response, should_continue = handle_command("what is today's date?")

    assert "Today is" in response
    assert should_continue is True


@patch("assistant.commands.webbrowser.open")
def test_open_github(mock_open):
    response, should_continue = handle_command("open github")

    mock_open.assert_called_once_with("https://github.com")
    assert response == "Opening GitHub."
    assert should_continue is True


def test_unknown_command():
    response, should_continue = handle_command("tell me a joke")

    assert "don't know" in response
    assert should_continue is True


def test_custom_command_from_config(tmp_path):
    config_path = tmp_path / "commands.json"
    config_path.write_text(
        json.dumps(
            {
                "commands": {
                    "open python": {
                        "response": "Opening Python's website.",
                        "url": "https://www.python.org",
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with (
        patch.object(commands, "CONFIG_PATH", config_path),
        patch("assistant.commands.webbrowser.open") as mock_open,
    ):
        response, should_continue = commands.handle_command("  OPEN   PYTHON ")

    mock_open.assert_called_once_with("https://www.python.org")
    assert response == "Opening Python's website."
    assert should_continue is True


def test_missing_config_returns_no_custom_commands(tmp_path):
    with patch.object(commands, "CONFIG_PATH", tmp_path / "missing.json"):
        assert commands.load_custom_commands() == {}
