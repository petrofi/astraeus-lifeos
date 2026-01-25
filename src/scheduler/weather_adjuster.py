"""
ASTRAEUS - Autonomous Life Orchestrator
Weather Adjuster Module

This module handles weather-based time adjustments
for travel and outdoor activities.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import structlog

from src.config import settings

logger = structlog.get_logger()


class WeatherCondition(Enum):
    """Weather condition types."""
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    HEAVY_SNOW = "heavy_snow"
    FOG = "fog"
    WIND = "wind"
    STORM = "storm"
    EXTREME_HEAT = "extreme_heat"
    EXTREME_COLD = "extreme_cold"


@dataclass
class WeatherAdjustment:
    """Weather-based time adjustment."""
    condition: WeatherCondition
    walking_buffer_percent: int
    driving_buffer_percent: int
    transit_buffer_percent: int
    recommendations: list
    warnings: list


class WeatherAdjuster:
    """
    Calculates time adjustments based on weather conditions.
    """
    
    # Weather condition mappings
    ADJUSTMENTS: Dict[WeatherCondition, WeatherAdjustment] = {
        WeatherCondition.CLEAR: WeatherAdjustment(
            condition=WeatherCondition.CLEAR,
            walking_buffer_percent=0,
            driving_buffer_percent=0,
            transit_buffer_percent=0,
            recommendations=["☀️ Hava güzel, keyfini çıkar!"],
            warnings=[]
        ),
        WeatherCondition.CLOUDY: WeatherAdjustment(
            condition=WeatherCondition.CLOUDY,
            walking_buffer_percent=0,
            driving_buffer_percent=0,
            transit_buffer_percent=0,
            recommendations=["☁️ Bulutlu ama yağmur yok"],
            warnings=[]
        ),
        WeatherCondition.RAIN: WeatherAdjustment(
            condition=WeatherCondition.RAIN,
            walking_buffer_percent=settings.rain_time_buffer,
            driving_buffer_percent=10,
            transit_buffer_percent=15,
            recommendations=[
                "☔ Şemsiye al",
                "🥾 Su geçirmez ayakkabı giy",
                "📱 Telefonunu koruyucu kılıfa koy"
            ],
            warnings=["Yollar kaygan olabilir"]
        ),
        WeatherCondition.HEAVY_RAIN: WeatherAdjustment(
            condition=WeatherCondition.HEAVY_RAIN,
            walking_buffer_percent=40,
            driving_buffer_percent=25,
            transit_buffer_percent=30,
            recommendations=[
                "🌧️ Mümkünse dışarı çıkma",
                "☔ Güçlü şemsiye veya yağmurluk al",
                "🚗 Toplu taşıma veya taksi düşün"
            ],
            warnings=[
                "⚠️ Sel riski olabilir",
                "⚠️ Görüş mesafesi düşük"
            ]
        ),
        WeatherCondition.SNOW: WeatherAdjustment(
            condition=WeatherCondition.SNOW,
            walking_buffer_percent=settings.snow_time_buffer,
            driving_buffer_percent=30,
            transit_buffer_percent=25,
            recommendations=[
                "❄️ Kalın giyin",
                "🧤 Eldiven ve bere tak",
                "🥾 Kaymaz ayakkabı giy"
            ],
            warnings=[
                "⚠️ Yollar kaygan",
                "⚠️ Dikkatli yürü"
            ]
        ),
        WeatherCondition.HEAVY_SNOW: WeatherAdjustment(
            condition=WeatherCondition.HEAVY_SNOW,
            walking_buffer_percent=50,
            driving_buffer_percent=50,
            transit_buffer_percent=40,
            recommendations=[
                "🌨️ Çok gerekli değilse dışarı çıkma",
                "❄️ Çok kalın giyin",
                "🔋 Telefonuna power bank al"
            ],
            warnings=[
                "🚨 Ulaşım aksamaları olabilir",
                "🚨 Dışarısı tehlikeli"
            ]
        ),
        WeatherCondition.FOG: WeatherAdjustment(
            condition=WeatherCondition.FOG,
            walking_buffer_percent=10,
            driving_buffer_percent=30,
            transit_buffer_percent=20,
            recommendations=[
                "🌫️ Görüş düşük, dikkatli ol",
                "🚗 Araç kullanıyorsan sis farlarını aç"
            ],
            warnings=["⚠️ Trafik daha yavaş olabilir"]
        ),
        WeatherCondition.WIND: WeatherAdjustment(
            condition=WeatherCondition.WIND,
            walking_buffer_percent=15,
            driving_buffer_percent=5,
            transit_buffer_percent=10,
            recommendations=[
                "💨 Rüzgarlık giy",
                "🧢 Şapka uçabilir, dikkat et"
            ],
            warnings=["⚠️ Bisiklet kullanma"]
        ),
        WeatherCondition.STORM: WeatherAdjustment(
            condition=WeatherCondition.STORM,
            walking_buffer_percent=50,
            driving_buffer_percent=40,
            transit_buffer_percent=50,
            recommendations=[
                "⛈️ DIŞARI ÇIKMA",
                "🏠 Güvenli bir yerde kal",
                "📱 Acil durumlar için şarjlı kal"
            ],
            warnings=[
                "🚨 Hava çok tehlikeli",
                "🚨 Zorunlu değilse evde kal"
            ]
        ),
        WeatherCondition.EXTREME_HEAT: WeatherAdjustment(
            condition=WeatherCondition.EXTREME_HEAT,
            walking_buffer_percent=20,
            driving_buffer_percent=0,
            transit_buffer_percent=10,
            recommendations=[
                "🥵 Bol su iç",
                "🧴 Güneş kremi sür",
                "🕶️ Şapka ve güneş gözlüğü tak",
                "⏰ Öğle saatlerinde gölgede kal"
            ],
            warnings=[
                "⚠️ Güneş çarpması riski",
                "⚠️ Fiziksel aktiviteyi azalt"
            ]
        ),
        WeatherCondition.EXTREME_COLD: WeatherAdjustment(
            condition=WeatherCondition.EXTREME_COLD,
            walking_buffer_percent=25,
            driving_buffer_percent=15,
            transit_buffer_percent=20,
            recommendations=[
                "🥶 Katman katman giyin",
                "🧣 Boyun ve baş bölgesini koru",
                "🧤 Eller ve ayakları sıcak tut",
                "☕ Sıcak içecek al"
            ],
            warnings=[
                "⚠️ Donma tehlikesi",
                "⚠️ Uzun süre dışarıda kalma"
            ]
        )
    }
    
    def __init__(self):
        logger.info("Weather adjuster initialized")
    
    def get_condition_from_data(
        self,
        weather_main: str,
        temperature: float,
        wind_speed: float = 0,
        description: str = ""
    ) -> WeatherCondition:
        """
        Determine weather condition from weather data.
        
        Args:
            weather_main: Main weather category (from API)
            temperature: Temperature in Celsius
            wind_speed: Wind speed in m/s
            description: Weather description
        
        Returns:
            Appropriate WeatherCondition enum
        """
        main_lower = weather_main.lower()
        desc_lower = description.lower()
        
        # Check for extreme temperatures first
        if temperature > 35:
            return WeatherCondition.EXTREME_HEAT
        if temperature < -5:
            return WeatherCondition.EXTREME_COLD
        
        # Check weather type
        if "storm" in main_lower or "thunder" in main_lower or "fırtına" in desc_lower:
            return WeatherCondition.STORM
        
        if "snow" in main_lower or "kar" in desc_lower:
            if "heavy" in desc_lower or "yoğun" in desc_lower:
                return WeatherCondition.HEAVY_SNOW
            return WeatherCondition.SNOW
        
        if "rain" in main_lower or "drizzle" in main_lower or "yağmur" in desc_lower:
            if "heavy" in desc_lower or "yoğun" in desc_lower or "şiddetli" in desc_lower:
                return WeatherCondition.HEAVY_RAIN
            return WeatherCondition.RAIN
        
        if "fog" in main_lower or "mist" in main_lower or "sis" in desc_lower:
            return WeatherCondition.FOG
        
        if wind_speed > 10:  # Strong wind threshold
            return WeatherCondition.WIND
        
        if "cloud" in main_lower or "bulut" in desc_lower:
            return WeatherCondition.CLOUDY
        
        return WeatherCondition.CLEAR
    
    def get_adjustment(
        self,
        condition: WeatherCondition
    ) -> WeatherAdjustment:
        """Get adjustment for a weather condition."""
        return self.ADJUSTMENTS.get(condition, self.ADJUSTMENTS[WeatherCondition.CLEAR])
    
    def calculate_buffer(
        self,
        condition: WeatherCondition,
        walking_minutes: int,
        transport_mode: str = "transit"
    ) -> int:
        """
        Calculate buffer time in minutes based on weather.
        
        Args:
            condition: Current weather condition
            walking_minutes: Base walking time
            transport_mode: Transport type (walking, driving, transit)
        
        Returns:
            Buffer time in minutes
        """
        adjustment = self.get_adjustment(condition)
        
        if transport_mode == "walking":
            percent = adjustment.walking_buffer_percent
        elif transport_mode == "driving":
            percent = adjustment.driving_buffer_percent
        else:
            percent = adjustment.transit_buffer_percent
        
        buffer = int(walking_minutes * percent / 100)
        
        # Minimum 5 minutes for bad weather
        if percent > 0 and buffer < 5:
            buffer = 5
        
        logger.debug(
            "Weather buffer calculated",
            condition=condition.value,
            base_minutes=walking_minutes,
            buffer_percent=percent,
            buffer_minutes=buffer
        )
        
        return buffer
    
    def format_weather_alert(
        self,
        condition: WeatherCondition,
        temperature: float
    ) -> str:
        """Format a weather alert message."""
        adjustment = self.get_adjustment(condition)
        
        parts = [f"🌤️ **Hava Durumu Uyarısı**", ""]
        
        # Temperature
        if temperature > 30:
            parts.append(f"🌡️ Sıcaklık: {temperature:.0f}°C (Sıcak)")
        elif temperature < 5:
            parts.append(f"🌡️ Sıcaklık: {temperature:.0f}°C (Soğuk)")
        else:
            parts.append(f"🌡️ Sıcaklık: {temperature:.0f}°C")
        
        # Warnings
        if adjustment.warnings:
            parts.append("")
            parts.append("⚠️ **Uyarılar:**")
            for warning in adjustment.warnings:
                parts.append(f"  {warning}")
        
        # Recommendations
        if adjustment.recommendations:
            parts.append("")
            parts.append("💡 **Öneriler:**")
            for rec in adjustment.recommendations:
                parts.append(f"  {rec}")
        
        # Time adjustment info
        if adjustment.walking_buffer_percent > 0:
            parts.append("")
            parts.append(f"⏱️ Yürüme süresine +{adjustment.walking_buffer_percent}% eklendi")
        
        return "\n".join(parts)


# Singleton instance
weather_adjuster = WeatherAdjuster()
