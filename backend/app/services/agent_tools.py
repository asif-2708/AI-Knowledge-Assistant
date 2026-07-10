import httpx
import re
from datetime import datetime

async def get_current_weather(location: str) -> str:
    try:
        # Step 1: Geocoding to get coordinates
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1&language=en&format=json"
        async with httpx.AsyncClient() as client:
            geo_response = await client.get(geocode_url, timeout=10.0)
            if geo_response.status_code != 200:
                return f"Could not find coordinates for '{location}' (Geocoding API HTTP error {geo_response.status_code})."
            
            geo_data = geo_response.json()
            if not geo_data.get("results"):
                return f"Location '{location}' not found."
            
            result = geo_data["results"][0]
            lat = result["latitude"]
            lon = result["longitude"]
            name = result["name"]
            country = result.get("country", "")
            timezone = result.get("timezone", "UTC")
            
            # Step 2: Weather Forecast
            weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true&timezone={timezone}"
            weather_response = await client.get(weather_url, timeout=10.0)
            if weather_response.status_code != 200:
                return f"Could not fetch weather data for {name} (Forecast API HTTP error {weather_response.status_code})."
                
            weather_data = weather_response.json()
            current = weather_data.get("current_weather")
            if not current:
                return f"No current weather data available for {name}."
                
            temp = current["temperature"]
            windspeed = current["windspeed"]
            code = current["weathercode"]
            
            descriptions = {
                0: "Clear sky",
                1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                45: "Fog", 48: "Depositing rime fog",
                51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                71: "Slight snow fall", 73: "Moderate snow fall", 75: "Heavy snow fall",
                77: "Snow grains",
                80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                85: "Slight snow showers", 86: "Heavy snow showers",
                95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"
            }
            desc = descriptions.get(code, "Unknown weather condition")
            
            return f"Current weather in {name}, {country} (Lat: {lat}, Lon: {lon}): Temperature is {temp}°C, condition is '{desc}', wind speed is {windspeed} km/h."
    except Exception as e:
        return f"Error fetching weather: {str(e)}"

def get_current_datetime() -> str:
    now = datetime.now()
    return f"Current local date and time: {now.strftime('%A, %B %d, %Y %I:%M:%S %p %Z')}"

def calculator(expression: str) -> str:
    try:
        # Sanitize expression: only allow numbers, math operators, dots, parenthesis, spaces
        sanitized = re.sub(r'[^0-9+\-*/().\s]', '', expression)
        if not sanitized.strip():
            return "Invalid expression."
        # Evaluate safely
        result = eval(sanitized, {"__builtins__": None}, {})
        return f"Calculation result: {expression} = {result}"
    except Exception as e:
        return f"Error evaluating expression '{expression}': {str(e)}"
