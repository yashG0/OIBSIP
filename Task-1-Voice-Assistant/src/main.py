import pyttsx3
import speech_recognition as sr
from dotenv import load_dotenv

from assistant.commands import handle_command


def speak(speaker, message: str) -> None:
    print(f"Assistant: {message}")
    if speaker is not None:
        try:
            speaker.say(message)
            speaker.runAndWait()
        except Exception as error:
            print(f"Speech output error: {error}")


def run_text_mode(speaker) -> None:
    speak(speaker, "Text mode enabled. Type a command.")

    while True:
        try:
            command = input("You: ").strip()
        except EOFError, KeyboardInterrupt:
            speak(speaker, "Goodbye!")
            break

        response, should_continue = handle_command(command)
        speak(speaker, response)

        if not should_continue:
            break


def run_voice_mode(speaker) -> None:
    recognizer = sr.Recognizer()

    with sr.Microphone() as microphone:
        print("Calibrating microphone...")
        recognizer.adjust_for_ambient_noise(
            microphone,
            duration=1,
        )

        speak(speaker, "Voice mode enabled. How can I help?")

        while True:
            try:
                print("Listening...")
                audio = recognizer.listen(
                    microphone,
                    timeout=5,
                    phrase_time_limit=8,
                )
                command = recognizer.recognize_google(audio)
                print(f"You: {command}")

                response, should_continue = handle_command(command)
                speak(speaker, response)

                if not should_continue:
                    break

            except sr.WaitTimeoutError:
                print("No speech detected.")

            except sr.UnknownValueError:
                speak(speaker, "I couldn't understand that. Please repeat.")

            except sr.RequestError as error:
                print(f"Recognition service error: {error}")
                speak(speaker, "Speech recognition is unavailable.")
                break


def main() -> None:
    load_dotenv()
    try:
        speaker = pyttsx3.init()
    except Exception as error:
        speaker = None
        print(f"Speech output unavailable: {error}")

    speak(speaker, "Voice assistant starting.")

    try:
        choice = input("Choose mode: [t]ext or [v]oice: ").strip().lower()

        if choice == "v":
            try:
                run_voice_mode()
            except (OSError, AttributeError) as error:
                print(f"Microphone unavailable: {error}")
                run_text_mode(speaker)
        else:
            run_text_mode(speaker)

    except KeyboardInterrupt:
        speak(speaker, "Goodbye!")


if __name__ == "__main__":
    main()
