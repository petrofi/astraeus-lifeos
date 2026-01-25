"""
ASTRAEUS - Autonomous Life Orchestrator
Weather API Module

This module integrates with OpenWeatherMap API
to provide real-time weather data.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict, Any
import httpx
import asyncio
import structlog

from src.config import settings

logger = structlog.get_logger()

# OpenWeatherMap API endpoints
OWM_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
OWM_FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"


@dataclass
class WeatherData:
    """Current weather data."""
    location: str
    temperature: float  # Celsius
    feels_like: float
    humidity: int  # Percentage
    pressure: int  # hPa
    wind_speed: float  # m/s
    wind_direction: int  # Degrees
    description: str
    main: str  # Main weather category
    icon: str
    visibility: int  # Meters
    clouds: int  # Percentage
    sunrise: Optional[datetime] = None
    sunset: Optional[datetime] = None
    rain_1h: float = 0  # Rain volume for last hour (mm)
    snow_1h: float = 0  # Snow volume for last hour (mm)
    
    @property
    def is_raining(self) -> bool:
        return self.rain_1h > 0 or "rain" in self.main.lower()
    
    @property
    def is_snowing(self) -> bool:
        return self.snow_1h > 0 or "snow" in self.main.lower()
    
    @property
    def is_bad_weather(self) -> bool:
        bad = ["rain", "snow", "storm", "thunder", "fog", "mist"]
        return any(b in self.main.lower() or b in self.description.lower() for b in bad)
    
    @property
    def emoji(self) -> str:
        """Get weather emoji based on conditions."""
        main_lower = self.main.lower()
        if "clear" in main_lower:
            return "☀️" if self.temperature > 25 else "🌤️"
        elif "cloud" in main_lower:
            return "☁️"
        elif "rain" in main_lower or "drizzle" in main_lower:
            return "🌧️" if "heavy" in self.description.lower() else "🌦️"
        elif "snow" in main_lower:
            return "❄️"
        elif "thunder" in main_lower:
            return "⛈️"
        elif "fog" in main_lower or "mist" in main_lower:
            return "🌫️"
        return "🌡️"
    
    def format_summary(self) -> str:
        """Format weather as readable summary."""
        return f"""{self.emoji} **{self.location}**
🌡️ Sıcaklık: {self.temperature:.1f}°C (Hissedilen: {self.feels_like:.1f}°C)
💧 Nem: {self.humidity}%
💨 Rüzgar: {self.wind_speed:.1f} m/s
📝 Durum: {self.description.capitalize()}"""


@dataclass
class ForecastItem:
    """Single forecast entry."""
    datetime: datetime
    temperature: float
    feels_like: float
    humidity: int
    description: str
    main: str
    rain_probability: float  # 0-1
    rain_3h: float = 0
    snow_3h: float = 0


class WeatherAPI:
    """
    OpenWeatherMap API client for weather data.
    """
    
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.openweathermap_api_key
        self.cache: Dict[str, tuple] = {}  # (data, timestamp)
        self.cache_ttl = 600  # 10 minutes
        
        if not self.api_key:
            logger.warning("OpenWeatherMap API key not configured")
        else:
            logger.info("Weather API initialized")
    
    async def get_current_weather(
        self,
        city: str = None,
        lat: float = None,
        lon: float = None
    ) -> Optional[WeatherData]:
        """
        Get current weather for a location.
        
        Args:
            city: City name (e.g., "Istanbul,TR")
            lat: Latitude (used if city not provided)
            lon: Longitude (used if city not provided)
        
        Returns:
            WeatherData object or None if failed
        """
        if not self.api_key:
            logger.error("Weather API key not configured")
            return None
        
        # Build request params
        params = {
            "appid": self.api_key,
            "units": "metric",  # Celsius
            "lang": "tr"  # Turkish descriptions
        }
        
        if city:
            params["q"] = city
            cache_key = f"weather:{city}"
        elif lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
            cache_key = f"weather:{lat:.3f},{lon:.3f}"
        else:
            city = f"{settings.default_city},{settings.default_country}"
            params["q"] = city
            cache_key = f"weather:{city}"
        
        # Check cache
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                logger.debug("Weather cache hit", key=cache_key)
                return data
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    OWM_CURRENT_URL,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            weather = self._parse_current_weather(data)
            
            # Cache result
            self.cache[cache_key] = (weather, datetime.now())
            
            logger.info(
                "Weather fetched",
                location=weather.location,
                temp=weather.temperature,
                condition=weather.main
            )
            
            return weather
            
        except httpx.HTTPError as e:
            logger.error("Weather API request failed", error=str(e))
            return None
        except Exception as e:
            logger.error("Weather parsing failed", error=str(e))
            return None
    
    async def get_forecast(
        self,
        city: str = None,
        lat: float = None,
        lon: float = None,
        hours: int = 24
    ) -> List[ForecastItem]:
        """
        Get weather forecast for a location.
        
        Args:
            city: City name
            lat: Latitude
            lon: Longitude
            hours: Number of hours to forecast (max 120)
        
        Returns:
            List of ForecastItem objects
        """
        if not self.api_key:
            return []
        
        params = {
            "appid": self.api_key,
            "units": "metric",
            "lang": "tr"
        }
        
        if city:
            params["q"] = city
        elif lat is not None and lon is not None:
            params["lat"] = lat
            params["lon"] = lon
        else:
            params["q"] = f"{settings.default_city},{settings.default_country}"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    OWM_FORECAST_URL,
                    params=params,
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            forecasts = []
            items_needed = hours // 3  # Forecast is 3-hour intervals
            
            for item in data.get("list", [])[:items_needed]:
                forecast = ForecastItem(
                    datetime=datetime.fromtimestamp(item["dt"]),
                    temperature=item["main"]["temp"],
                    feels_like=item["main"]["feels_like"],
                    humidity=item["main"]["humidity"],
                    description=item["weather"][0]["description"],
                    main=item["weather"][0]["main"],
                    rain_probability=item.get("pop", 0),
                    rain_3h=item.get("rain", {}).get("3h", 0),
                    snow_3h=item.get("snow", {}).get("3h", 0)
                )
                forecasts.append(forecast)
            
            logger.info(f"Fetched {len(forecasts)} forecast items")
            return forecasts
            
        except Exception as e:
            logger.error("Forecast fetch failed", error=str(e))
            return []
    
    def _parse_current_weather(self, data: Dict[str, Any]) -> WeatherData:
        """Parse API response into WeatherData."""
        main = data.get("main", {})
        wind = data.get("wind", {})
        weather = data.get("weather", [{}])[0]
        sys = data.get("sys", {})
        
        sunrise = None
        sunset = None
        if sys.get("sunrise"):
            sunrise = datetime.fromtimestamp(sys["sunrise"])
        if sys.get("sunset"):
            sunset = datetime.fromtimestamp(sys["sunset"])
        
        return WeatherData(
            location=data.get("name", "Unknown"),
            temperature=main.get("temp", 0),
            feels_like=main.get("feels_like", 0),
            humidity=main.get("humidity", 0),
            pressure=main.get("pressure", 0),
            wind_speed=wind.get("speed", 0),
            wind_direction=wind.get("deg", 0),
            description=weather.get("description", ""),
            main=weather.get("main", ""),
            icon=weather.get("icon", ""),
            visibility=data.get("visibility", 10000),
            clouds=data.get("clouds", {}).get("all", 0),
            sunrise=sunrise,
            sunset=sunset,
            rain_1h=data.get("rain", {}).get("1h", 0),
            snow_1h=data.get("snow", {}).get("1h", 0)
        )
    
    async def get_weather_alert(
        self,
        city: str = None,
        lat: float = None,
        lon: float = None
    ) -> Optional[str]:
        """
        Check if there are any weather alerts/warnings.
        Returns formatted alert message if severe weather detected.
        """
        weather = await self.get_current_weather(city, lat, lon)
        
        if not weather:
            return None
        
        alerts = []
        
        # Temperature alerts
        if weather.temperature > 35:
            alerts.append("🥵 Aşırı sıcak! Bol su iç ve güneşten korun.")
        elif weather.temperature < 0:
            alerts.append("🥶 Dondurucu soğuk! Kalın giyin.")
        
        # Rain/snow alerts
        if weather.is_raining:
            alerts.append("☔ Yağmur yağıyor! Şemsiyeni al.")
        if weather.is_snowing:
            alerts.append("❄️ Kar yağıyor! Dikkatli ol, yollar kaygan.")
        
        # Wind alert
        if weather.wind_speed > 10:
            alerts.append(f"💨 Kuvvetli rüzgar ({weather.wind_speed:.0f} m/s)!")
        
        # Storm alert
        if "storm" in weather.main.lower() or "thunder" in weather.main.lower():
            alerts.append("⛈️ FIRTINA UYARISI! Mümkünse dışarı çıkma.")
        
        # Low visibility
        if weather.visibility < 1000:
            alerts.append("🌫️ Görüş mesafesi çok düşük!")
        
        if alerts:
            return f"⚠️ **Hava Durumu Uyarısı - {weather.location}**\n\n" + "\n".join(alerts)
        
        return None
    
    def format_for_prompt(self, weather: WeatherData) -> str:
        """Format weather data for AI system prompt injection."""
        return f"""Şu anki hava durumu ({weather.location}):
- Sıcaklık: {weather.temperature:.1f}°C (Hissedilen: {weather.feels_like:.1f}°C)
- Durum: {weather.description}
- Yağmur: {'Evet' if weather.is_raining else 'Hayır'}
- Kar: {'Evet' if weather.is_snowing else 'Hayır'}
- Rüzgar: {weather.wind_speed:.1f} m/s
- Nem: {weather.humidity}%"""


# Singleton instance
weather_api = WeatherAPI()
