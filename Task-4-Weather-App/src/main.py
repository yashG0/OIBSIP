import io
import threading
import tkinter as tk
from tkinter import ttk
from urllib.request import urlopen

import requests
from PIL import Image, ImageTk

from weather_app.api import (
    WeatherAPIError,
    get_current_weather,
    get_forecast,
)

BG = "#0b1220"
PANEL = "#151f32"
TEXT = "#f1f5f9"
MUTED = "#9baac0"
ACCENT = "#7dd3fc"


class WeatherApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Atmos — Weather")
        self.geometry("900x720")
        self.minsize(700, 600)
        self.configure(bg=BG)

        self.unit = tk.StringVar(value="C")
        self.city = tk.StringVar()
        self.status = tk.StringVar(value="Search for a city to see its weather.")
        self.current = None
        self.icon_refs = []

        self._build_ui()

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "Weather.TCombobox",
            fieldbackground=PANEL,
            background=PANEL,
            foreground=TEXT,
        )

        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=28, pady=(24, 14))

        tk.Label(
            header, text="ATMOS", bg=BG, fg=ACCENT, font=("Inter", 12, "bold")
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Weather, at a glance.",
            bg=BG,
            fg=TEXT,
            font=("Inter", 25, "bold"),
        ).pack(anchor="w", pady=(5, 0))

        search = tk.Frame(self, bg=PANEL, padx=12, pady=12)
        search.pack(fill="x", padx=28, pady=8)

        self.city_entry = tk.Entry(
            search,
            textvariable=self.city,
            bg=PANEL,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            font=("Inter", 12),
            highlightthickness=0,
        )
        self.city_entry.pack(side="left", fill="x", expand=True, padx=8, ipady=8)
        self.city_entry.insert(0, "")

        self.search_button = tk.Button(
            search,
            text="Get weather",
            command=self.search_weather,
            bg=ACCENT,
            fg=BG,
            activebackground="#bae6fd",
            relief="flat",
            font=("Inter", 10, "bold"),
            padx=16,
            pady=9,
            cursor="hand2",
        )
        self.search_button.pack(side="left", padx=5)

        self.unit_button = tk.Button(
            search,
            text="°C / °F",
            command=self.toggle_unit,
            bg="#26354c",
            fg=TEXT,
            relief="flat",
            padx=12,
            pady=9,
            cursor="hand2",
        )
        self.unit_button.pack(side="left", padx=5)

        self.error_label = tk.Label(
            self,
            textvariable=self.status,
            bg=BG,
            fg=MUTED,
            font=("Inter", 10),
            anchor="w",
        )
        self.error_label.pack(fill="x", padx=32, pady=(2, 10))

        self.current_panel = tk.Frame(self, bg=PANEL, padx=24, pady=20)
        self.current_panel.pack(fill="x", padx=28, pady=5)

        self.location_label = tk.Label(
            self.current_panel,
            text="Your location",
            bg=PANEL,
            fg=MUTED,
            font=("Inter", 12),
        )
        self.location_label.pack(anchor="w")

        self.temperature_label = tk.Label(
            self.current_panel,
            text="--°",
            bg=PANEL,
            fg=TEXT,
            font=("Inter", 48, "bold"),
        )
        self.temperature_label.pack(anchor="w")

        self.condition_label = tk.Label(
            self.current_panel,
            text="Search a city to begin",
            bg=PANEL,
            fg=ACCENT,
            font=("Inter", 14),
        )
        self.condition_label.pack(anchor="w")

        self.details_label = tk.Label(
            self.current_panel,
            text="Humidity --  ·  Wind --",
            bg=PANEL,
            fg=MUTED,
            font=("Inter", 10),
        )
        self.details_label.pack(anchor="w", pady=(12, 0))

        forecast_heading = tk.Frame(self, bg=BG)
        forecast_heading.pack(fill="x", padx=28, pady=(18, 8))
        tk.Label(
            forecast_heading,
            text="UPCOMING",
            bg=BG,
            fg=TEXT,
            font=("Inter", 13, "bold"),
        ).pack(side="left")
        tk.Label(
            forecast_heading,
            text="3-hour intervals · 5-day outlook",
            bg=BG,
            fg=MUTED,
            font=("Inter", 9),
        ).pack(side="right")

        self.forecast_panel = tk.Frame(self, bg=BG)
        self.forecast_panel.pack(fill="both", expand=True, padx=28, pady=(0, 18))

        self.hourly_frame = tk.Frame(self.forecast_panel, bg=BG)
        self.hourly_frame.pack(fill="x", pady=(0, 12))
        self.daily_frame = tk.Frame(self.forecast_panel, bg=BG)
        self.daily_frame.pack(fill="both", expand=True)

        self.city_entry.bind("<Return>", lambda _event: self.search_weather())

    def search_weather(self):
        city = self.city.get().strip()
        if not city:
            self.show_error("Enter a city name or ZIP code.")
            return

        self.search_button.configure(state="disabled", text="Loading…")
        self.status.set("Fetching weather data…")
        self.error_label.configure(fg=MUTED)

        threading.Thread(target=self.fetch_weather, args=(city,), daemon=True).start()

    def fetch_weather(self, city):
        try:
            current = get_current_weather(city)
            forecast = get_forecast(city)
            self.after(0, lambda: self.show_weather(current, forecast))
        except WeatherAPIError as exc:
            self.after(0, lambda message=str(exc): self.show_error(message))
        except KeyError, TypeError, ValueError:
            self.after(
                0,
                lambda: self.show_error(
                    "The weather service returned unexpected data."
                ),
            )
        finally:
            self.after(
                0,
                lambda: self.search_button.configure(
                    state="normal", text="Get weather"
                ),
            )

    def show_weather(self, current, forecast):
        self.current = current
        self.location_label.configure(
            text=f"{current['city']}, {current['country']}".strip(", ")
        )
        self.condition_label.configure(text=current["description"])
        self.details_label.configure(
            text=(
                f"Feels like {self.temperature(current['feels_like_c'])}"
                f"    ·    Humidity {current['humidity']}%"
                f"    ·    Wind {current['wind_speed']} m/s"
            )
        )
        self.update_temperature()
        self.status.set("Weather updated successfully.")
        self.error_label.configure(fg=ACCENT)
        self.render_forecasts(forecast)

        # Load the current-condition icon without blocking the main window.
        threading.Thread(
            target=self.load_icon,
            args=(current["icon_url"],),
            daemon=True,
        ).start()

    def load_icon(self, url):
        try:
            with urlopen(url, timeout=5) as response:
                image_data = response.read()
            image = Image.open(io.BytesIO(image_data)).resize((70, 70))
            photo = ImageTk.PhotoImage(image)
            self.after(0, lambda: self.set_icon(photo))
        except OSError, requests.RequestException:
            pass

    def set_icon(self, photo):
        self.icon_refs = [photo]
        if hasattr(self, "icon_label"):
            self.icon_label.destroy()
        self.icon_label = tk.Label(self.current_panel, image=photo, bg=PANEL)
        self.icon_label.place(relx=0.93, rely=0.12, anchor="center")

    def temperature(self, celsius):
        if self.unit.get() == "F":
            return f"{celsius * 9 / 5 + 32:.1f}°F"
        return f"{celsius:.1f}°C"

    def update_temperature(self):
        if self.current:
            self.temperature_label.configure(
                text=self.temperature(self.current["temperature_c"])
            )

    def toggle_unit(self):
        self.unit.set("F" if self.unit.get() == "C" else "C")
        self.update_temperature()
        if self.current:
            self.render_forecasts(self.last_forecast)

    def render_forecasts(self, forecast):
        self.last_forecast = forecast

        for frame in (self.hourly_frame, self.daily_frame):
            for widget in frame.winfo_children():
                widget.destroy()

        for index, item in enumerate(forecast["hourly"]):
            self.forecast_card(
                self.hourly_frame,
                item["time"][5:16],
                self.temperature(item["temperature_c"]),
                item["description"],
                index,
            )

        for index, item in enumerate(forecast["daily"]):
            self.forecast_card(
                self.daily_frame,
                item["date"],
                f"{self.temperature(item['temperature_min_c'])} / "
                f"{self.temperature(item['temperature_max_c'])}",
                item["description"],
                index,
            )

    def forecast_card(self, parent, title, temperature, description, index):
        card = tk.Frame(parent, bg=PANEL, padx=12, pady=12)
        card.pack(
            side="left", fill="both", expand=True, padx=(0 if index == 0 else 7, 0)
        )

        tk.Label(
            card,
            text=title,
            bg=PANEL,
            fg=MUTED,
            font=("Inter", 9),
        ).pack(anchor="w")
        tk.Label(
            card,
            text=temperature,
            bg=PANEL,
            fg=TEXT,
            font=("Inter", 13, "bold"),
        ).pack(anchor="w", pady=(7, 4))
        tk.Label(
            card,
            text=description,
            bg=PANEL,
            fg=ACCENT,
            font=("Inter", 9),
            wraplength=130,
            justify="left",
        ).pack(anchor="w")

    def show_error(self, message):
        self.status.set(message)
        self.error_label.configure(fg="#fca5a5")


if __name__ == "__main__":
    app = WeatherApp()
    app.mainloop()
