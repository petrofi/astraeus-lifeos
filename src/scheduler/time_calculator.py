"""
ASTRAEUS - Autonomous Life Orchestrator
Time Calculator Module

This module implements the core time calculation formula:
T_kalkış = T_etkinlik - (T_ulaşım + T_yürüme + T_hazırlık + T_tampon)
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Tuple
import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass
class TimeCalculation:
    """Result of a time calculation."""
    event_time: datetime
    departure_time: datetime
    travel_duration: timedelta
    walking_duration: timedelta
    prep_time: timedelta
    buffer_time: timedelta
    total_duration: timedelta
    
    @property
    def time_until_departure(self) -> timedelta:
        """Time remaining until departure."""
        now = datetime.now()
        return self.departure_time - now
    
    @property
    def is_urgent(self) -> bool:
        """Check if departure is within 15 minutes."""
        return self.time_until_departure <= timedelta(minutes=15)
    
    @property
    def is_overdue(self) -> bool:
        """Check if departure time has passed."""
        return self.time_until_departure < timedelta(0)
    
    def format_summary(self) -> str:
        """Format calculation as readable summary."""
        total_min = int(self.total_duration.total_seconds() / 60)
        travel_min = int(self.travel_duration.total_seconds() / 60)
        walk_min = int(self.walking_duration.total_seconds() / 60)
        prep_min = int(self.prep_time.total_seconds() / 60)
        buffer_min = int(self.buffer_time.total_seconds() / 60)
        
        parts = [
            f"⏰ Etkinlik: {self.event_time.strftime('%H:%M')}",
            f"🚀 Kalkış: {self.departure_time.strftime('%H:%M')}",
            f"",
            f"📊 Süre Dağılımı:",
            f"  🚌 Ulaşım: {travel_min} dk",
            f"  🚶 Yürüme: {walk_min} dk",
            f"  👔 Hazırlık: {prep_min} dk",
        ]
        
        if buffer_min > 0:
            parts.append(f"  ⚡ Tampon: {buffer_min} dk")
        
        parts.append(f"  ─────────────")
        parts.append(f"  📍 Toplam: {total_min} dk")
        
        return "\n".join(parts)


class TimeCalculator:
    """
    Core time calculation engine.
    Computes optimal departure times considering all factors.
    """
    
    def __init__(self, default_prep_time: int = None):
        self.default_prep_time = timedelta(
            minutes=default_prep_time or settings.default_prep_time
        )
        logger.info("Time calculator initialized", prep_time=self.default_prep_time)
    
    def calculate_departure(
        self,
        event_time: datetime,
        travel_minutes: int,
        walking_minutes: int = 0,
        prep_minutes: Optional[int] = None,
        buffer_minutes: int = 0
    ) -> TimeCalculation:
        """
        Calculate optimal departure time.
        
        Formula: T_kalkış = T_etkinlik - (T_ulaşım + T_yürüme + T_hazırlık + T_tampon)
        
        Args:
            event_time: When the event starts
            travel_minutes: Travel time (bus, car, etc.)
            walking_minutes: Walking time to/from stops
            prep_minutes: Preparation time (default from settings)
            buffer_minutes: Extra buffer time (weather, traffic)
        
        Returns:
            TimeCalculation object with all details
        """
        travel = timedelta(minutes=travel_minutes)
        walking = timedelta(minutes=walking_minutes)
        prep = timedelta(minutes=prep_minutes) if prep_minutes else self.default_prep_time
        buffer = timedelta(minutes=buffer_minutes)
        
        total = travel + walking + prep + buffer
        departure = event_time - total
        
        calculation = TimeCalculation(
            event_time=event_time,
            departure_time=departure,
            travel_duration=travel,
            walking_duration=walking,
            prep_time=prep,
            buffer_time=buffer,
            total_duration=total
        )
        
        logger.debug(
            "Departure calculated",
            event=event_time.isoformat(),
            departure=departure.isoformat(),
            total_minutes=int(total.total_seconds() / 60)
        )
        
        return calculation
    
    def calculate_with_weather(
        self,
        event_time: datetime,
        travel_minutes: int,
        walking_minutes: int,
        weather_condition: str,
        is_raining: bool = False,
        is_snowing: bool = False,
        prep_minutes: Optional[int] = None
    ) -> TimeCalculation:
        """
        Calculate departure time with weather-adjusted buffer.
        
        Args:
            event_time: When the event starts
            travel_minutes: Travel time
            walking_minutes: Walking time
            weather_condition: Current weather description
            is_raining: Whether it's raining
            is_snowing: Whether it's snowing
            prep_minutes: Preparation time
        
        Returns:
            TimeCalculation with weather adjustment
        """
        # Calculate buffer based on weather
        buffer_percent = 0
        
        if is_raining or "rain" in weather_condition.lower() or "yağmur" in weather_condition.lower():
            buffer_percent = max(buffer_percent, settings.rain_time_buffer)
        
        if is_snowing or "snow" in weather_condition.lower() or "kar" in weather_condition.lower():
            buffer_percent = max(buffer_percent, settings.snow_time_buffer)
        
        # Apply buffer percentage to walking time primarily
        buffer_minutes = int(walking_minutes * buffer_percent / 100)
        
        # Add minimum 5 minute buffer in bad weather
        if buffer_percent > 0 and buffer_minutes < 5:
            buffer_minutes = 5
        
        logger.info(
            "Weather buffer applied",
            weather=weather_condition,
            buffer_percent=buffer_percent,
            buffer_minutes=buffer_minutes
        )
        
        return self.calculate_departure(
            event_time=event_time,
            travel_minutes=travel_minutes,
            walking_minutes=walking_minutes,
            prep_minutes=prep_minutes,
            buffer_minutes=buffer_minutes
        )
    
    def calculate_latest_departure(
        self,
        event_time: datetime,
        travel_minutes: int,
        walking_minutes: int = 0
    ) -> datetime:
        """
        Calculate the absolute latest departure time (no buffer).
        This is for emergency calculations.
        
        Returns:
            Latest possible departure time
        """
        travel = timedelta(minutes=travel_minutes)
        walking = timedelta(minutes=walking_minutes)
        
        return event_time - (travel + walking)
    
    def time_until_departure(
        self,
        departure_time: datetime,
        current_time: Optional[datetime] = None
    ) -> Tuple[timedelta, str]:
        """
        Calculate time remaining until departure and format it.
        
        Returns:
            Tuple of (timedelta, formatted string)
        """
        current = current_time or datetime.now()
        remaining = departure_time - current
        
        total_seconds = int(remaining.total_seconds())
        
        if total_seconds < 0:
            minutes = abs(total_seconds) // 60
            return remaining, f"⚠️ {minutes} dakika geç!"
        
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        if hours > 0:
            formatted = f"{hours} saat {minutes} dakika"
        else:
            formatted = f"{minutes} dakika"
        
        return remaining, formatted
    
    def format_countdown(self, departure_time: datetime) -> str:
        """Format a countdown message to departure."""
        remaining, formatted = self.time_until_departure(departure_time)
        
        if remaining < timedelta(0):
            return f"🚨 Kalkış zamanı geçti! {formatted}"
        elif remaining < timedelta(minutes=5):
            return f"🔴 HEMEN ÇIK! {formatted} kaldı"
        elif remaining < timedelta(minutes=15):
            return f"🟡 Hazırlan! {formatted} kaldı"
        elif remaining < timedelta(minutes=30):
            return f"🟢 {formatted} sonra kalkış"
        else:
            return f"⏳ Kalkışa {formatted} var"


# Singleton instance
time_calculator = TimeCalculator()
