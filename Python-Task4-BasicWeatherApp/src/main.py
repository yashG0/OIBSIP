from PyQt5.QtWidgets import QApplication

from weather_app.gui import AtmosApp


def main() -> None:
    app = QApplication([])
    app.setApplicationName("Atmos")
    window = AtmosApp()
    window.show()
    app.exec_()


if __name__ == "__main__":
    main()
