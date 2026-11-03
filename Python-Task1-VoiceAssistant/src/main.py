"""Entry point for the text and voice modes."""

from __future__ import annotations

import queue
import threading
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

import pyttsx3
import speech_recognition as sr
from dotenv import load_dotenv

from assistant.commands import CommandProcessor

class SpeechOutput:
    """Own the TTS engine on one worker thread, including reminder speech."""

    def __init__(self) -> None:
        self.messages: queue.Queue[tuple[str, threading.Event] | None] = queue.Queue()
        self.ready = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        self.ready.wait(timeout=5)

    def _run(self) -> None:
        try:
            engine = pyttsx3.init()
            # Prefer a clear English voice when available and use a measured pace.
            try:
                # eSpeak's f3 variant provides a feminine US English voice.
                engine.setProperty("voice", "en-us+f3")
            except (ValueError, RuntimeError):
                # Fall back to the standard English voice on other TTS engines.
                voices = engine.getProperty("voices")
                english_voice = next(
                    (voice for voice in voices if "en-us" in getattr(voice, "id", "")),
                    None,
                )
                if english_voice is not None:
                    engine.setProperty("voice", english_voice.id)
            engine.setProperty("rate", 200)
            engine.setProperty("volume", 1.0)
        except Exception as error:
            engine = None
            print(f"Speech output unavailable: {error}")
        finally:
            self.ready.set()

        while True:
            item = self.messages.get()
            if item is None:
                return
            message, finished = item
            try:
                if engine is not None:
                    engine.say(message)
                    engine.runAndWait()
            except Exception as error:
                print(f"Speech output error: {error}")
            finally:
                finished.set()

    def say(self, message: str) -> None:
        if not self.ready.wait(timeout=5):
            print("Speech output did not start.")
            return
        finished = threading.Event()
        self.messages.put((message, finished))
        finished.wait()


def speak(speaker: SpeechOutput | None, message: str) -> None:
    """Print and speak a response; keep reminder speech serialized."""
    print(f"Assistant: {message}")
    if speaker is not None:
        speaker.say(message)


@contextmanager
def microphone_source() -> Iterator[sr.Microphone]:
    """Open a microphone and avoid SpeechRecognition closing a missing stream."""
    source = sr.Microphone()
    source.__enter__()
    if source.stream is None:
        # SpeechRecognition currently swallows PortAudio's open error in
        # Microphone.__enter__; detect the failed stream before using/closing it.
        source.audio = None
        raise OSError(
            "No microphone input device is available. Connect or enable a mic, "
            "or choose text mode."
        )
    try:
        yield source
    finally:
        if source.stream is not None:
            source.__exit__(None, None, None)


def run_text_mode(speaker, processor: CommandProcessor) -> None:
    speak(speaker, "Text mode enabled. Type a command or say help.")
    while True:
        try:
            command = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            speak(speaker, "Goodbye!")
            return
        response, should_continue = processor.handle(command)
        speak(speaker, response)
        if not should_continue:
            return


def run_voice_mode(speaker, processor: CommandProcessor) -> bool:
    """Listen and respond. Return False when text mode should take over."""
    recognizer = sr.Recognizer()
    recognizer.dynamic_energy_threshold = True
    with microphone_source() as microphone:
        print("Calibrating microphone for background noise…")
        recognizer.adjust_for_ambient_noise(microphone, duration=1)
        speak(speaker, "Voice mode enabled. How can I help?")

        while True:
            try:
                print("Listening…")
                audio = recognizer.listen(microphone, timeout=5, phrase_time_limit=10)
                command = recognizer.recognize_google(audio)
                print(f"You: {command}")
                response, should_continue = processor.handle(command)
                speak(speaker, response)
                if not should_continue:
                    return True
            except sr.WaitTimeoutError:
                print("No speech detected. Listening again…")
            except sr.UnknownValueError:
                speak(speaker, "I couldn't understand that. Please repeat.")
            except sr.RequestError as error:
                print(f"Speech recognition service error: {error}")
                speak(speaker, "Speech recognition is unavailable. Switching to text mode.")
                return False


def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    load_dotenv(project_root / ".env")

    speaker = SpeechOutput()

    processor = CommandProcessor(on_reminder=lambda message: speak(speaker, message))
    speak(speaker, "Voice assistant ready.")
    try:
        choice = input("Choose mode: [v]oice or [t]ext: ").strip().casefold()
        if choice == "v":
            try:
                should_continue_in_voice = run_voice_mode(speaker, processor)
            except (OSError, AttributeError) as error:
                print(f"Microphone unavailable: {error}")
                should_continue_in_voice = False
            if not should_continue_in_voice:
                run_text_mode(speaker, processor)
        elif choice in {"t", "text"}:
            run_text_mode(speaker, processor)
        else:
            speak(speaker, "Please choose voice or text mode.")
    except KeyboardInterrupt:
        speak(speaker, "Goodbye!")


if __name__ == "__main__":
    main()
