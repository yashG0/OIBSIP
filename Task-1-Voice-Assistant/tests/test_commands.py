from unittest.mock import patch

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
