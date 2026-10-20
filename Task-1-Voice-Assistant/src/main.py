import pyttsx3
import speech_recognition as sr

from assistant.commands import handle_command


def main() -> None:
    try:
        speaker = pyttsx3.init()
    except Exception as error:
        speaker = None
        print(f"Speech output unavailable: {error}")

    def speak(message: str) -> None:
        print(f"Assistant: {message}")
        if speaker is not None:
            try:
                speaker.say(message)
                speaker.runAndWait()
            except Exception as error:
                print(f"Speech output error: {error}")

    def run_text_mode() -> None:
        speak("Text mode enabled. Type a command.")

        while True:
            try:
                command = input("You: ").strip()
            except EOFError, KeyboardInterrupt:
                speak("Goodbye!")
                break

            response, should_continue = handle_command(command)
            speak(response)

            if not should_continue:
                break

    def run_voice_mode() -> None:
        recognizer = sr.Recognizer()

        with sr.Microphone() as microphone:
            print("Calibrating microphone...")
            recognizer.adjust_for_ambient_noise(
                microphone,
                duration=1,
            )

            speak("Voice mode enabled. How can I help?")

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
                    speak(response)

                    if not should_continue:
                        break

                except sr.WaitTimeoutError:
                    print("No speech detected.")

                except sr.UnknownValueError:
                    speak("I couldn't understand that. Please repeat.")

                except sr.RequestError as error:
                    print(f"Recognition service error: {error}")
                    speak("Speech recognition is unavailable.")
                    break

    speak("Voice assistant starting.")

    try:
        choice = input("Choose mode: [t]ext or [v]oice: ").strip().lower()

        if choice == "v":
            try:
                run_voice_mode()
            except (OSError, AttributeError) as error:
                print(f"Microphone unavailable: {error}")
                run_text_mode()
        else:
            run_text_mode()

    except KeyboardInterrupt:
        speak("Goodbye!")


if __name__ == "__main__":
    main()
