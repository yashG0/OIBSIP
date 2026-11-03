# Atmos — Weather

A desktop weather app built with Python and PyQt5. Search by city or ZIP code to see current conditions, weather details, the upcoming forecast, and the next five days.

## Setup

1. Install the project dependencies:

   ```bash
   uv sync
   ```

   Or install them with pip:

   ```bash
   pip install PyQt5 requests python-dotenv
   ```

2. Create a `.env` file in the project root and add your OpenWeatherMap API key:

   ```env
   OPENWEATHERMAP_API_KEY=your_api_key_here
   ```

3. Start the app:

   ```bash
   uv run python src/main.py
   ```

The app also supports Celsius/Fahrenheit switching. Weather-service errors appear in the window.
