"""PyQt5 interface for the Atmos weather application."""

from __future__ import annotations

import urllib.request
from datetime import date, datetime
from typing import Any

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, Qt, pyqtSignal
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from weather_app.api import WeatherAPIError, get_current_weather, get_forecast


class _WorkerSignals(QObject):
    finished = pyqtSignal(dict, dict, dict)
    failed = pyqtSignal(str)


class _WeatherWorker(QRunnable):
    """Fetch weather data and icons without blocking the window."""

    def __init__(self, city: str):
        super().__init__()
        self.city = city
        self.signals = _WorkerSignals()

    def run(self) -> None:
        try:
            current = get_current_weather(self.city)
            forecast = get_forecast(self.city)
            urls = [current.get("icon_url", "")]
            urls += [item.get("icon_url", "") for item in forecast["hourly"]]
            urls += [item.get("icon_url", "") for item in forecast["daily"]]
            images: dict[str, bytes] = {}
            for url in urls:
                if not url or url in images:
                    continue
                try:
                    with urllib.request.urlopen(url, timeout=5) as response:
                        images[url] = response.read()
                except Exception:
                    images[url] = b""
            self.signals.finished.emit(current, forecast, images)
        except WeatherAPIError as exc:
            self.signals.failed.emit(str(exc))
        except Exception:
            self.signals.failed.emit("Unable to load weather. Please try again.")


class AtmosApp(QMainWindow):
    """Main weather window and its presentation logic."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Atmos · Weather")
        self.setMinimumSize(680, 680)
        self.resize(1040, 900)
        self.unit = "C"
        self.current: dict[str, Any] | None = None
        self.forecast: dict[str, list[dict[str, Any]]] = {"hourly": [], "daily": []}
        self.icon_data: dict[str, bytes] = {}
        self.busy = False
        self.thread_pool = QThreadPool.globalInstance()
        self._build_ui()

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.setCentralWidget(scroll)

        page = QWidget()
        page.setObjectName("page")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(32, 22, 32, 28)
        page_layout.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        scroll.setWidget(page)

        content = QWidget()
        content.setMaximumWidth(1240)
        content.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        page_layout.addWidget(content)
        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(16)

        header = QHBoxLayout()
        branding = QVBoxLayout()
        branding.setSpacing(2)
        title = QLabel("Atmos")
        title.setObjectName("brand")
        tagline = QLabel("Weather, at a glance")
        tagline.setObjectName("muted")
        branding.addWidget(title)
        branding.addWidget(tagline)
        header.addLayout(branding)
        header.addStretch()
        self.unit_button = QPushButton("°C")
        self.unit_button.setObjectName("unitButton")
        self.unit_button.setFixedSize(58, 42)
        self.unit_button.clicked.connect(self.toggle_unit)
        header.addWidget(self.unit_button, alignment=Qt.AlignBottom)
        root.addLayout(header)

        search = QHBoxLayout()
        search.setSpacing(9)
        self.city_entry = QLineEdit()
        self.city_entry.setPlaceholderText("Search a city or ZIP code")
        self.city_entry.setClearButtonEnabled(True)
        self.city_entry.returnPressed.connect(self.search)
        search.addWidget(self.city_entry, 1)
        self.search_button = QPushButton("Get weather")
        self.search_button.setObjectName("primaryButton")
        self.search_button.setMinimumWidth(132)
        self.search_button.clicked.connect(self.search)
        search.addWidget(self.search_button)
        root.addLayout(search)

        self.status_label = QLabel("Search for a city to see its current weather and forecast.")
        self.status_label.setObjectName("statusLabel")
        root.addWidget(self.status_label)

        self.hero = QFrame()
        self.hero.setObjectName("hero")
        hero_layout = QHBoxLayout(self.hero)
        hero_layout.setContentsMargins(26, 22, 26, 22)
        details = QVBoxLayout()
        self.location_label = QLabel("Your local forecast")
        self.location_label.setObjectName("location")
        self.condition_label = QLabel("Search for a city to get started")
        self.condition_label.setObjectName("heroMuted")
        self.temperature_label = QLabel("--°")
        self.temperature_label.setObjectName("temperature")
        self.feels_label = QLabel("Feels like —")
        self.feels_label.setObjectName("heroMuted")
        for widget in (self.location_label, self.condition_label):
            details.addWidget(widget)
        details.addSpacing(6)
        details.addWidget(self.temperature_label)
        details.addWidget(self.feels_label)
        hero_layout.addLayout(details, 1)
        self.current_icon = QLabel("☁")
        self.current_icon.setObjectName("currentIcon")
        self.current_icon.setAlignment(Qt.AlignCenter)
        self.current_icon.setFixedSize(116, 116)
        hero_layout.addWidget(self.current_icon)
        root.addWidget(self.hero)

        metrics = QGridLayout()
        metrics.setSpacing(12)
        humidity_card, self.humidity_value = self._metric_card("Humidity", "—")
        wind_card, self.wind_value = self._metric_card("Wind", "—")
        condition_card, self.condition_value = self._metric_card("Conditions", "—")
        metrics.addWidget(humidity_card, 0, 0)
        metrics.addWidget(wind_card, 0, 1)
        metrics.addWidget(condition_card, 0, 2)
        root.addLayout(metrics)

        root.addWidget(self._section_title("Coming up", "Next forecast periods"))
        self.hourly_placeholder = QLabel("Your upcoming forecast will appear here.")
        self.hourly_placeholder.setObjectName("emptyHint")
        self.hourly_placeholder.setAlignment(Qt.AlignCenter)
        self.hourly_placeholder.setMinimumHeight(64)
        root.addWidget(self.hourly_placeholder)
        self.hourly_row = QHBoxLayout()
        self.hourly_row.setSpacing(12)
        root.addLayout(self.hourly_row)

        root.addWidget(self._section_title("Next five days", "Daily high and low"))
        self.daily_row = QHBoxLayout()
        self.daily_row.setSpacing(10)
        root.addLayout(self.daily_row)
        root.addStretch(1)
        self.setStyleSheet(STYLESHEET)

    def _metric_card(self, label: str, value: str) -> tuple[QFrame, QLabel]:
        card = QFrame()
        card.setObjectName("metricCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        name = QLabel(label.upper())
        name.setObjectName("eyebrow")
        result = QLabel(value)
        result.setObjectName("metricValue")
        layout.addWidget(name)
        layout.addWidget(result)
        return card, result

    def _section_title(self, title: str, detail: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 4, 0, 0)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        description = QLabel(detail)
        description.setObjectName("muted")
        layout.addWidget(heading)
        layout.addStretch()
        layout.addWidget(description)
        return row

    def search(self) -> None:
        city = self.city_entry.text().strip()
        if not city:
            self._set_status("Enter a city name or ZIP code.", error=True)
            return
        if self.busy:
            return

        self.busy = True
        self.search_button.setEnabled(False)
        self.search_button.setText("Loading…")
        self._set_status(f"Checking the latest weather for {city}…")
        worker = _WeatherWorker(city)
        worker.signals.finished.connect(self._show_weather)
        worker.signals.failed.connect(self._show_error)
        self.thread_pool.start(worker)

    def _show_weather(self, current: dict, forecast: dict, images: dict) -> None:
        self.current = current
        self.forecast = forecast
        self.icon_data = images
        location = current["city"]
        if current.get("country"):
            location += f", {current['country']}"
        self.location_label.setText(location)
        self.condition_label.setText(current["description"])
        self.temperature_label.setText(self._temperature(current["temperature_c"]))
        self.feels_label.setText(f"Feels like {self._temperature(current['feels_like_c'])}")
        self.humidity_value.setText(f"{current['humidity']}%")
        self.wind_value.setText(f"{current['wind_speed']:g} m/s")
        self.condition_value.setText(current["description"])
        self._set_icon(self.current_icon, current.get("icon_url", ""), 116)
        self._render_forecasts()
        self._set_status(f"Updated just now · {location}")
        self._finish_loading()

    def _show_error(self, message: str) -> None:
        self._set_status(message, error=True)
        self._finish_loading()

    def _finish_loading(self) -> None:
        self.busy = False
        self.search_button.setEnabled(True)
        self.search_button.setText("Get weather")

    def _temperature(self, celsius: float) -> str:
        if self.unit == "F":
            return f"{celsius * 9 / 5 + 32:.0f}°F"
        return f"{celsius:.0f}°C"

    def toggle_unit(self) -> None:
        self.unit = "F" if self.unit == "C" else "C"
        self.unit_button.setText(f"°{self.unit}")
        if self.current:
            self.temperature_label.setText(self._temperature(self.current["temperature_c"]))
            self.feels_label.setText(f"Feels like {self._temperature(self.current['feels_like_c'])}")
            self._render_forecasts()

    def _set_icon(self, label: QLabel, url: str, size: int = 48) -> None:
        data = self.icon_data.get(url, b"")
        pixmap = QPixmap()
        if data and pixmap.loadFromData(data):
            label.setText("")
            label.setPixmap(pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            label.setPixmap(QPixmap())
            label.setText("☁")

    @staticmethod
    def _clear_layout(layout: QHBoxLayout | QGridLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _render_forecasts(self) -> None:
        self._clear_layout(self.hourly_row)
        self._clear_layout(self.daily_row)
        hourly = self.forecast["hourly"]
        self.hourly_placeholder.setVisible(not hourly)
        for item in hourly:
            self.hourly_row.addWidget(self._forecast_card(
                item["time"][-8:-3], self._temperature(item["temperature_c"]),
                item["description"], item.get("icon_url", ""),
            ), 1)
        today = date.today()
        for item in self.forecast["daily"]:
            forecast_day = date.fromisoformat(item["date"])
            day_label = "Today" if forecast_day == today else forecast_day.strftime("%a, %b %d").replace(" 0", " ")
            self.daily_row.addWidget(self._daily_card(
                day_label,
                f"{self._temperature(item['temperature_min_c'])} / "
                f"{self._temperature(item['temperature_max_c'])}",
                item["description"], item.get("icon_url", ""),
            ), 1)

    def _forecast_card(self, title: str, temperature: str, description: str,
                       icon_url: str, compact: bool = False) -> QFrame:
        card = QFrame()
        card.setObjectName("forecastCard")
        layout = QHBoxLayout(card) if compact else QVBoxLayout(card)
        layout.setContentsMargins(14, 13, 14, 13)
        icon = QLabel()
        icon.setFixedSize(42 if compact else 48, 42 if compact else 48)
        if compact:
            text_layout = QVBoxLayout()
            layout.addWidget(icon)
            layout.addLayout(text_layout, 1)
            labels = (QLabel(title), QLabel(temperature), QLabel(description))
            labels[1].setObjectName("forecastValue")
            labels[2].setObjectName("muted")
            for label in labels:
                text_layout.addWidget(label)
        else:
            time_label = QLabel(title)
            time_label.setObjectName("muted")
            value_label = QLabel(temperature)
            value_label.setObjectName("forecastValue")
            description_label = QLabel(description)
            description_label.setObjectName("muted")
            description_label.setWordWrap(True)
            for widget in (time_label, icon, value_label, description_label):
                layout.addWidget(widget)
        self._set_icon(icon, icon_url, 42 if compact else 48)
        return card

    def _daily_card(self, day: str, temperature: str, description: str,
                    icon_url: str) -> QFrame:
        card = QFrame()
        card.setObjectName("dailyCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 13)
        layout.setSpacing(5)
        day_label = QLabel(day)
        day_label.setObjectName("dayLabel")
        day_label.setAlignment(Qt.AlignCenter)
        icon = QLabel()
        icon.setFixedSize(46, 46)
        icon.setAlignment(Qt.AlignCenter)
        value = QLabel(temperature)
        value.setObjectName("dailyValue")
        value.setAlignment(Qt.AlignCenter)
        condition = QLabel(description)
        condition.setObjectName("muted")
        condition.setAlignment(Qt.AlignCenter)
        condition.setWordWrap(True)
        for widget in (day_label, icon, value, condition):
            layout.addWidget(widget)
        self._set_icon(icon, icon_url, 44)
        return card

    def _set_status(self, message: str, error: bool = False) -> None:
        self.status_label.setText(message)
        self.status_label.setProperty("error", error)
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)


STYLESHEET = """
QMainWindow, QWidget#page { background: #17191e; color: #f4f5f7; }
QWidget { font-family: 'Inter', 'Noto Sans', sans-serif; font-size: 14px; }
QLabel { color: #f4f5f7; background: transparent; }
QLabel#brand { font-size: 28px; font-weight: 750; color: #f8fafc; }
QLabel#muted, QLabel#heroMuted, QLabel#statusLabel { color: #a8afb9; }
QLabel#heroMuted { color: #bfd0d4; font-size: 15px; }
QLabel[error="true"] { color: #ff938c; }
QLineEdit { background: #22262d; color: #f4f5f7; border: 1px solid #343a44; border-radius: 13px; padding: 12px 16px; selection-background-color: #278da1; }
QLineEdit:focus { border: 1px solid #38b9cc; }
QPushButton { background: #292d35; color: #f4f5f7; border: 1px solid #373c46; border-radius: 12px; padding: 10px 16px; font-weight: 650; }
QPushButton:hover { background: #343944; }
QPushButton:disabled { color: #9ba1aa; background: #282b31; }
QPushButton#primaryButton { background: #168da1; border: 0; color: white; }
QPushButton#primaryButton:hover { background: #20a0b4; }
QPushButton#unitButton { background: #292d35; font-weight: 700; }
QLabel#location { font-size: 22px; font-weight: 700; }
QLabel#temperature { font-size: 60px; font-weight: 750; }
QLabel#currentIcon { font-size: 76px; color: #dbeafe; }
QFrame#hero { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #203d45, stop:1 #1d3039); border: 1px solid #29464e; border-radius: 21px; }
QFrame#metricCard, QFrame#forecastCard, QFrame#dailyCard { background: #22252c; border: 1px solid #30343d; border-radius: 15px; }
QLabel#eyebrow { color: #9da5af; font-size: 11px; font-weight: 700; letter-spacing: 1px; }
QLabel#metricValue, QLabel#forecastValue, QLabel#dailyValue { font-size: 17px; font-weight: 700; }
QLabel#sectionTitle { font-size: 18px; font-weight: 700; }
QLabel#dayLabel { color: #c5cbd4; font-weight: 650; font-size: 12px; }
QFrame#dailyCard:hover, QFrame#forecastCard:hover { background: #282d35; border-color: #3b4652; }
QLabel#emptyHint { background: #20232a; border: 1px dashed #414751; border-radius: 14px; color: #9da5af; }
QScrollArea { border: 0; }
QScrollBar:vertical { background: #17191e; width: 10px; margin: 4px; }
QScrollBar::handle:vertical { background: #3c424d; border-radius: 5px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
"""
