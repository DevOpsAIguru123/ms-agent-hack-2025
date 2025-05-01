import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# AccuWeather API key
accuweather_api_key = os.getenv("ACCUWEATHER_API_KEY")

def get_location_key(city):
    """Get the AccuWeather location key for a city."""
    try:
        url = f"http://dataservice.accuweather.com/locations/v1/cities/search"
        params = {
            "apikey": accuweather_api_key,
            "q": city
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            return None, f"Error: Location API request failed with status code {response.status_code}. Response: {response.text}"
        
        locations = response.json()
        
        if not locations:
            return None, f"No location found for '{city}'"
        
        # Get the first (most relevant) location
        location_key = locations[0]["Key"]
        location_name = f"{locations[0]['LocalizedName']}, {locations[0]['Country']['LocalizedName']}"
        
        return location_key, location_name
    
    except Exception as e:
        return None, f"Error getting location key: {str(e)}"

def get_forecast(location_key, location_name):
    """Get 5-day forecast for a location using AccuWeather API."""
    try:
        url = f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}"
        params = {
            "apikey": accuweather_api_key,
            "details": "true",
            "metric": "true"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            return f"Error: Forecast API request failed with status code {response.status_code}. Response: {response.text}"
        
        forecast_data = response.json()
        
        if not forecast_data or "DailyForecasts" not in forecast_data:
            return "Error: No forecast data returned"
        
        # Extract tomorrow's forecast (index 1)
        tomorrow = forecast_data["DailyForecasts"][0]
        
        # Get temperature and weather details
        min_temp = tomorrow["Temperature"]["Minimum"]["Value"]
        max_temp = tomorrow["Temperature"]["Maximum"]["Value"]
        day_condition = tomorrow["Day"]["IconPhrase"]
        chance_of_rain = tomorrow["Day"].get("RainProbability", 0)
        
        # Weather advice
        advice = ""
        if chance_of_rain > 30:
            advice = " Don't forget your umbrella!"
        if max_temp > 30:
            advice += " It's going to be hot, so drink plenty of water."
        
        forecast_info = f"Tomorrow's weather in {location_name}: {day_condition}, with temperatures between {min_temp}°C and {max_temp}°C. Chance of rain: {chance_of_rain}%.{advice}"
        
        return forecast_info
    
    except Exception as e:
        return f"Error getting forecast: {str(e)}"

def get_weather(city):
    """Get current weather and tomorrow's forecast for a city using AccuWeather API."""
    try:
        # First get the location key for the city
        location_key, location_result = get_location_key(city)
        
        if location_key is None:
            return location_result  # This contains the error message
        
        # Get tomorrow's forecast
        forecast_info = get_forecast(location_key, location_result)
        
        # Now get the current conditions
        url = f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}"
        params = {
            "apikey": accuweather_api_key,
            "details": "true"
        }
        
        response = requests.get(url, params=params)
        
        if response.status_code != 200:
            return forecast_info  # Return just the forecast if current conditions fail
        
        current_conditions = response.json()
        
        if not current_conditions:
            return forecast_info  # Return just the forecast if current conditions are empty
        
        # Extract weather information from the first item
        weather_data = current_conditions[0]
        
        weather_text = weather_data.get("WeatherText", "Unknown condition")
        temperature_c = weather_data.get("Temperature", {}).get("Metric", {}).get("Value", "N/A")
        
        current_weather = f"Current weather in {location_result}: {weather_text}, {temperature_c}°C\n\n"
        
        return current_weather + forecast_info
    
    except requests.exceptions.RequestException as e:
        return f"Network error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

# Usage example:
if __name__ == "__main__":
    print(get_weather("Houston"))