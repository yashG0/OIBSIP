import io
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk
from urllib.request import urlopen

from PIL import Image, ImageTk

from weather_app.api import (
    WeatherAPIError,
    get_current_weather,
    get_forecast,
)

BG = "#242424"
CARD = "#303030"
BORDER = "#414141"
TEXT = "#F6F5F4"
MUTED = "#C0BFBC"
ACCENT = "#78AEED"
ERROR = "#F28B82"


class AtmosApp(tk.Tk):
    UI_FONT = "Inter"

    def __init__(self):
        super().__init__()

        self.title("Atmos — Weather")
        self.geometry("900x760")
        self.minsize(650, 650)
        self.configure(bg=BG)

        self.city = tk.StringVar()
        self.unit = tk.StringVar(value="C")
        self.status = tk.StringVar(value="Search for a city to get started.")

        self.current = None
        self.forecast = {"hourly": [], "daily": []}
        self.images = []
        self.busy = False
        self._configure_fonts()
        self._build_ui()

    def _configure_fonts(self):
        self.option_add("*Font", (self.UI_FONT, 10))

        style = ttk.Style(self)
        style.theme_use("clam")

        style.configure(
            ".",
            font=(self.UI_FONT, 10),
        )
        style.configure(
            "TButton",
            font=(self.UI_FONT, 10),
        )
        style.configure(
            "Atmos.TEntry",
            fieldbackground=CARD,
            background=CARD,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=10,
            font=(self.UI_FONT, 11),
        )
        style.map(
            "Atmos.TEntry",
            fieldbackground=[
                ("disabled", CARD),
                ("readonly", CARD),
                ("!disabled", CARD),
            ],
            foreground=[
                ("disabled", MUTED),
                ("!disabled", TEXT),
            ],
        )

    def _build_ui(self):
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True, padx=28, pady=24)

        header = tk.Frame(outer, bg=BG)
        header.pack(fill="x", pady=(0, 20))

        tk.Label(
            header,
            text="Atmos",
            bg=BG,
            fg=TEXT,
            font=(self.UI_FONT, 24, "bold"),
        ).pack(side="left")

        tk.Label(
            header,
            text="WEATHER OVERVIEW",
            bg=BG,
            fg=MUTED,
            font=(self.UI_FONT, 9, "bold"),
        ).pack(side="right", pady=(12, 0))

        search = tk.Frame(
            outer,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
        )
        search.pack(fill="x", pady=(0, 12))

        self.entry = ttk.Entry(
            search,
            textvariable=self.city,
            style="Atmos.TEntry",
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(6, 4), pady=6)
        self.entry.bind("<Return>", lambda _event: self.search())

        self.search_button = tk.Button(
            search,
            text="Get Weather",
            command=self.search,
            bg=ACCENT,
            fg="#181818",
            activebackground="#A8C9F0",
            activeforeground="#181818",
            relief="flat",
            bd=0,
            font=(self.UI_FONT, 10, "bold"),
            padx=16,
            pady=10,
            cursor="hand2",
        )
        self.search_button.pack(side="left", padx=(4, 6), pady=6)

        self.unit_button = tk.Button(
            search,
            text="°C",
            command=self.toggle_unit,
            bg="#454545",
            fg=TEXT,
            activebackground="#555555",
            activeforeground=TEXT,
            relief="flat",
            bd=0,
            font=(self.UI_FONT, 10, "bold"),
            padx=14,
            pady=10,
            cursor="hand2",
        )
        self.unit_button.pack(side="left", padx=(0, 6), pady=6)

        # Create the status label once. set_status() only updates it.
        self.status_label = tk.Label(
            outer,
            textvariable=self.status,
            bg=BG,
            fg=MUTED,
            font=(self.UI_FONT, 10),
            anchor="w",
        )
        self.status_label.pack(fill="x", pady=(0, 12))

        self.current_card = tk.Frame(
            outer,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=22,
            pady=20,
        )
        self.current_card.pack(fill="x")

        top = tk.Frame(self.current_card, bg=CARD)
        top.pack(fill="x")

        location_area = tk.Frame(top, bg=CARD)
        location_area.pack(side="left", fill="x", expand=True)

        self.location_label = tk.Label(
            location_area,
            text="Your location",
            bg=CARD,
            fg=TEXT,
            font=(self.UI_FONT, 18, "bold"),
        )
        self.location_label.pack(anchor="w")

        self.condition_label = tk.Label(
            location_area,
            text="Current conditions will appear here",
            bg=CARD,
            fg=MUTED,
            font=(self.UI_FONT, 11),
        )
        self.condition_label.pack(anchor="w", pady=(5, 0))

        self.icon_label = tk.Label(top, bg=CARD)
        self.icon_label.pack(side="right", padx=(8, 4))

        self.temperature_label = tk.Label(
            self.current_card,
            text="--°",
            bg=CARD,
            fg=TEXT,
            font=(self.UI_FONT, 42, "bold"),
        )
        self.temperature_label.pack(anchor="w", pady=(8, 0))

        self.feels_label = tk.Label(
            self.current_card,
            text="Feels like —",
            bg=CARD,
            fg=MUTED,
            font=(self.UI_FONT, 11),
        )
        self.feels_label.pack(anchor="w", pady=(0, 16))

        tk.Frame(self.current_card, bg=BORDER, height=1).pack(fill="x")

        metrics = tk.Frame(self.current_card, bg=CARD)
        metrics.pack(fill="x", pady=(15, 0))

        self.humidity_value = self._metric(metrics, "HUMIDITY", "—")
        self.wind_value = self._metric(metrics, "WIND", "—")
        self.condition_value = self._metric(metrics, "CONDITION", "—")

        forecast_header = tk.Frame(outer, bg=BG)
        forecast_header.pack(fill="x", pady=(24, 10))

        tk.Label(
            forecast_header,
            text="Forecast",
            bg=BG,
            fg=TEXT,
            font=(self.UI_FONT, 16, "bold"),
        ).pack(side="left")

        tk.Label(
            forecast_header,
            text="3-hour intervals · 5-day outlook",
            bg=BG,
            fg=MUTED,
            font=(self.UI_FONT, 9),
        ).pack(side="right", pady=(5, 0))

        tk.Label(
            outer,
            text="UP NEXT",
            bg=BG,
            fg=MUTED,
            font=(self.UI_FONT, 9, "bold"),
        ).pack(anchor="w", pady=(0, 8))

        self.hourly_frame = tk.Frame(outer, bg=BG)
        self.hourly_frame.pack(fill="x")

        tk.Label(
            outer,
            text="NEXT FIVE DAYS",
            bg=BG,
            fg=MUTED,
            font=(self.UI_FONT, 9, "bold"),
        ).pack(anchor="w", pady=(18, 8))

        self.daily_frame = tk.Frame(outer, bg=BG)
        self.daily_frame.pack(fill="x")

    def _metric(self, parent, label, initial):
        frame = tk.Frame(parent, bg=CARD)
        frame.pack(side="left", fill="x", expand=True)

        tk.Label(
            frame,
            text=label,
            bg=CARD,
            fg=MUTED,
            font=(self.UI_FONT, 9, "bold"),
        ).pack(anchor="w")

        value = tk.Label(
            frame,
            text=initial,
            bg=CARD,
            fg=TEXT,
            font=(self.UI_FONT, 12, "bold"),
        )
        value.pack(anchor="w", pady=(5, 0))
        return value

    def search(self):
        city = self.city.get().strip()

        if not city:
            self.set_status("Enter a city name or ZIP code.", error=True)
            return

        if self.busy:
            return

        self.busy = True  # type: ignore
        self.search_button.configure(state="disabled", text="Loading…")
        self.set_status("Fetching weather data…")

        threading.Thread(
            target=self._fetch,
            args=(city,),
            daemon=True,
        ).start()

    def _fetch(self, city):
        try:
            current = get_current_weather(city)
            forecast = get_forecast(city)

            self.after(0, lambda: self._show_weather(current, forecast))
        except WeatherAPIError as exc:
            message = str(exc)
            self.after(0, lambda: self.set_status(message, error=True))
        except Exception:
            self.after(
                0,
                lambda: self.set_status(
                    "Unable to display weather data. Please try again.",
                    error=True,
                ),
            )
        finally:
            self.after(0, self._finish_loading)

    def _finish_loading(self):
        self.busy = False  # type: ignore
        self.search_button.configure(state="normal", text="Get Weather")

    def _show_weather(self, current, forecast):
        self.current = current
        self.forecast = forecast

        location = current["city"]
        if current.get("country"):
            location += f", {current['country']}"

        self.location_label.configure(text=location)
        self.condition_label.configure(text=current["description"])
        self.feels_label.configure(
            text=("Feels like " + self._temperature(current["feels_like_c"]))
        )
        self.humidity_value.configure(text=f"{current['humidity']}%")
        self.wind_value.configure(text=f"{current['wind_speed']} m/s")
        self.condition_value.configure(text=current["description"])

        self._update_temperature()
        self._render_forecasts()
        self.set_status("Weather updated.")

        # Network downloads run off the Tk main thread.
        threading.Thread(
            target=self._load_icons,
            args=(current, forecast),
            daemon=True,
        ).start()

    def _load_icons(self, current, forecast):
        urls = [current.get("icon_url", "")]
        urls += [item.get("icon_url", "") for item in forecast["hourly"]]
        urls += [item.get("icon_url", "") for item in forecast["daily"]]

        loaded = []

        for url in urls:
            try:
                if not url:
                    loaded.append(None)
                    continue

                with urlopen(url, timeout=5) as response:
                    data = response.read()

                image = Image.open(io.BytesIO(data)).convert("RGBA")
                image.thumbnail((42, 42))
                loaded.append(image)
            except Exception:
                loaded.append(None)

        # PhotoImage objects are created later on the main thread.
        self.after(0, lambda: self._apply_icons(loaded))

    def _apply_icons(self, images):
        self.images = [
            ImageTk.PhotoImage(image) if image is not None else None for image in images
        ]

        if self.images and self.images[0]:
            self.icon_label.configure(image=self.images[0])

        groups = (
            (1, self.forecast["hourly"]),
            (
                1 + len(self.forecast["hourly"]),
                self.forecast["daily"],
            ),
        )

        for start, items in groups:
            for index, item in enumerate(items):
                image = self.images[start + index]
                item["_photo"] = image

                widget = item.get("_icon_widget")
                if image and widget and widget.winfo_exists():
                    widget.configure(image=image)

    def _temperature(self, celsius):
        if self.unit.get() == "F":
            fahrenheit = celsius * 9 / 5 + 32
            return f"{fahrenheit:.1f}°F"

        return f"{celsius:.1f}°C"

    def _update_temperature(self):
        if not self.current:
            return

        self.temperature_label.configure(
            text=self._temperature(self.current["temperature_c"])
        )
        self.feels_label.configure(
            text=("Feels like " + self._temperature(self.current["feels_like_c"]))
        )

    def toggle_unit(self):
        self.unit.set("F" if self.unit.get() == "C" else "C")
        self.unit_button.configure(text=f"°{self.unit.get()}")
        self._update_temperature()
        self._render_forecasts()

    def _render_forecasts(self):
        for frame in (self.hourly_frame, self.daily_frame):
            for widget in frame.winfo_children():
                widget.destroy()

        for item in self.forecast["hourly"]:
            time_text = item["time"]
            card = self._forecast_card(
                self.hourly_frame,
                time_text[-8:-3],
                self._temperature(item["temperature_c"]),
                item["description"],
            )
            item["_icon_widget"] = card["icon"]

        for item in self.forecast["daily"]:
            card = self._forecast_card(
                self.daily_frame,
                item["date"],
                (
                    f"{self._temperature(item['temperature_min_c'])}"
                    " / "
                    f"{self._temperature(item['temperature_max_c'])}"
                ),
                item["description"],
            )
            item["_icon_widget"] = card["icon"]

        # Restore cached icons after cards are rebuilt.
        for item in self.forecast["hourly"] + self.forecast["daily"]:
            photo = item.get("_photo")
            widget = item.get("_icon_widget")

            if photo and widget:
                widget.configure(image=photo)

    def _forecast_card(self, parent, title, temperature, description):
        card = tk.Frame(
            parent,
            bg=CARD,
            highlightbackground=BORDER,
            highlightthickness=1,
            padx=12,
            pady=12,
        )
        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8),
        )

        tk.Label(
            card,
            text=title,
            bg=CARD,
            fg=MUTED,
            font=(self.UI_FONT, 9),
        ).pack(anchor="w")

        icon = tk.Label(card, bg=CARD, width=4, height=2)
        icon.pack(anchor="w", pady=(5, 2))

        tk.Label(
            card,
            text=temperature,
            bg=CARD,
            fg=TEXT,
            font=(self.UI_FONT, 11, "bold"),
        ).pack(anchor="w")

        tk.Label(
            card,
            text=description,
            bg=CARD,
            fg=MUTED,
            font=(self.UI_FONT, 9),
            wraplength=115,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        return {"icon": icon}

    def set_status(self, message, error=False):
        self.status.set(message)
        self.status_label.configure(fg=ERROR if error else MUTED)


if __name__ == "__main__":
    app = AtmosApp()
    app.mainloop()
