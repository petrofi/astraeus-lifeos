"""
ASTRAEUS - Autonomous Life Orchestrator
Decision Engine Module

This module contains the proactive decision logic that powers
the intelligent notifications and recommendations.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import structlog

from src.config import settings

logger = structlog.get_logger()


class DecisionType(Enum):
    """Types of decisions the engine can make."""
    DEPARTURE_REMINDER = "departure_reminder"
    WEATHER_WARNING = "weather_warning"
    SCHEDULE_CONFLICT = "schedule_conflict"
    REPLAN_NEEDED = "replan_needed"
    ENERGY_SUGGESTION = "energy_suggestion"
    BREAK_REMINDER = "break_reminder"


class Urgency(Enum):
    """Urgency levels for notifications."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Decision:
    """Represents a decision made by the engine."""
    decision_type: DecisionType
    urgency: Urgency
    title: str
    message: str
    action_required: bool
    deadline: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.decision_type.value,
            "urgency": self.urgency.value,
            "title": self.title,
            "message": self.message,
            "action_required": self.action_required,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "metadata": self.metadata or {}
        }


@dataclass
class Event:
    """Represents a scheduled event."""
    id: str
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    location_coords: Optional[tuple] = None  # (lat, lon)
    priority: int = 1  # 1-5, 5 being highest
    notes: Optional[str] = None


@dataclass
class TravelInfo:
    """Information about travel to an event."""
    duration_minutes: int
    walking_minutes: int
    transport_type: str
    transport_line: Optional[str] = None
    departure_time: Optional[datetime] = None
    weather_buffer_minutes: int = 0


class DecisionEngine:
    """
    The brain's decision-making module.
    Analyzes context and generates proactive recommendations.
    """
    
    def __init__(self, user_name: str = None):
        self.user_name = user_name or settings.user_name
        self.prep_time = timedelta(minutes=settings.default_prep_time)
        self.min_warning = timedelta(minutes=settings.min_warning_time)
        logger.info("Decision engine initialized", user_name=self.user_name)
    
    def calculate_departure_time(
        self,
        event_time: datetime,
        travel_info: TravelInfo,
        include_buffer: bool = True
    ) -> datetime:
        """
        Calculate optimal departure time using the formula:
        T_kalkış = T_etkinlik - (T_ulaşım + T_yürüme + T_hazırlık + T_tampon)
        
        Args:
            event_time: When the event starts
            travel_info: Travel duration information
            include_buffer: Whether to include weather/traffic buffer
        
        Returns:
            Optimal departure datetime
        """
        total_travel = timedelta(minutes=travel_info.duration_minutes)
        walking = timedelta(minutes=travel_info.walking_minutes)
        buffer = timedelta(minutes=travel_info.weather_buffer_minutes) if include_buffer else timedelta()
        
        departure = event_time - (total_travel + walking + self.prep_time + buffer)
        
        logger.debug(
            "Departure time calculated",
            event_time=event_time.isoformat(),
            departure_time=departure.isoformat(),
            total_minutes=(total_travel + walking + self.prep_time + buffer).total_seconds() / 60
        )
        
        return departure
    
    def should_notify_departure(
        self,
        event: Event,
        travel_info: TravelInfo,
        current_time: Optional[datetime] = None
    ) -> Optional[Decision]:
        """
        Check if user should be notified about upcoming departure.
        
        Returns a Decision if notification is needed, None otherwise.
        """
        current_time = current_time or datetime.now()
        departure_time = self.calculate_departure_time(event.start_time, travel_info)
        
        time_until_departure = departure_time - current_time
        
        # Check various notification thresholds
        if time_until_departure <= timedelta(0):
            # Already past departure time!
            return Decision(
                decision_type=DecisionType.DEPARTURE_REMINDER,
                urgency=Urgency.CRITICAL,
                title="🚨 HEMEN ÇIKMALISIN!",
                message=self._format_critical_departure(event, travel_info),
                action_required=True,
                deadline=departure_time,
                metadata={"event_id": event.id, "late_by_minutes": -int(time_until_departure.total_seconds() / 60)}
            )
        
        elif time_until_departure <= timedelta(minutes=5):
            return Decision(
                decision_type=DecisionType.DEPARTURE_REMINDER,
                urgency=Urgency.HIGH,
                title="⏰ Kalkma Zamanı!",
                message=self._format_departure_reminder(event, travel_info, 5),
                action_required=True,
                deadline=departure_time,
                metadata={"event_id": event.id}
            )
        
        elif time_until_departure <= self.min_warning:
            minutes_left = int(time_until_departure.total_seconds() / 60)
            return Decision(
                decision_type=DecisionType.DEPARTURE_REMINDER,
                urgency=Urgency.MEDIUM,
                title="🕐 Hazırlık Zamanı",
                message=self._format_departure_reminder(event, travel_info, minutes_left),
                action_required=True,
                deadline=departure_time,
                metadata={"event_id": event.id}
            )
        
        return None
    
    def _format_critical_departure(self, event: Event, travel_info: TravelInfo) -> str:
        """Format a critical departure notification."""
        return f"""{self.user_name}, {event.title} için çoktan yola çıkmış olmalıydın! 🚨

📍 Hedef: {event.location or 'Belirtilmemiş'}
⏰ Etkinlik saati: {event.start_time.strftime('%H:%M')}
🚌 Ulaşım: {travel_info.transport_line or travel_info.transport_type}

HEMEN harekete geç! Her dakika önemli."""

    def _format_departure_reminder(
        self,
        event: Event,
        travel_info: TravelInfo,
        minutes_left: int
    ) -> str:
        """Format a departure reminder message."""
        weather_note = ""
        if travel_info.weather_buffer_minutes > 0:
            weather_note = f"\n☔ Hava durumu nedeniyle +{travel_info.weather_buffer_minutes} dakika tampon eklendi."
        
        transport_info = f"{travel_info.transport_line}" if travel_info.transport_line else travel_info.transport_type
        
        return f"""{self.user_name}, {minutes_left} dakika içinde kalkman gerekiyor! 🚀

📋 {event.title}
⏰ Saat: {event.start_time.strftime('%H:%M')}
📍 Konum: {event.location or 'Belirtilmemiş'}

🚌 Ulaşım: {transport_info}
🚶 Yürüme: {travel_info.walking_minutes} dakika
🕐 Toplam yolculuk: {travel_info.duration_minutes + travel_info.walking_minutes} dakika{weather_note}

Hazırlanmaya başla!"""

    def check_schedule_conflicts(
        self,
        events: List[Event],
        travel_infos: Dict[str, TravelInfo]
    ) -> List[Decision]:
        """
        Check for conflicts between scheduled events.
        
        Args:
            events: List of events sorted by start time
            travel_infos: Dict mapping event_id to travel info
        
        Returns:
            List of conflict decisions
        """
        conflicts = []
        
        for i in range(len(events) - 1):
            current = events[i]
            next_event = events[i + 1]
            
            # Calculate when we'd need to leave the current event
            next_travel = travel_infos.get(next_event.id)
            if not next_travel:
                continue
            
            needed_departure = self.calculate_departure_time(
                next_event.start_time,
                next_travel
            )
            
            current_end = current.end_time or (current.start_time + timedelta(hours=1))
            
            if needed_departure < current_end:
                overlap_minutes = int((current_end - needed_departure).total_seconds() / 60)
                conflicts.append(Decision(
                    decision_type=DecisionType.SCHEDULE_CONFLICT,
                    urgency=Urgency.HIGH if overlap_minutes > 15 else Urgency.MEDIUM,
                    title="⚠️ Program Çakışması",
                    message=f"""{self.user_name}, programında bir çakışma var!

'{current.title}' etkinliği {current_end.strftime('%H:%M')}'de bitiyor,
ama '{next_event.title}' için {needed_departure.strftime('%H:%M')}'de çıkman gerekiyor.

Bu {overlap_minutes} dakikalık bir çakışma yaratıyor!

Öneri: '{current.title}' etkinliğinden {overlap_minutes + 5} dakika erken ayrıl.""",
                    action_required=True,
                    metadata={
                        "current_event_id": current.id,
                        "next_event_id": next_event.id,
                        "overlap_minutes": overlap_minutes
                    }
                ))
        
        return conflicts

    def suggest_replan(
        self,
        original_departure: datetime,
        actual_departure: datetime,
        event: Event,
        travel_info: TravelInfo
    ) -> Decision:
        """
        Generate a replanning suggestion when the user is running late.
        """
        delay = actual_departure - original_departure
        delay_minutes = int(delay.total_seconds() / 60)
        
        new_arrival = event.start_time + delay
        
        return Decision(
            decision_type=DecisionType.REPLAN_NEEDED,
            urgency=Urgency.HIGH,
            title="🔄 Plan Güncellemesi",
            message=f"""{self.user_name}, {delay_minutes} dakika geç kaldın, ama endişelenme!

📊 Durum Analizi:
- Planlanan kalkış: {original_departure.strftime('%H:%M')}
- Gerçek kalkış: {actual_departure.strftime('%H:%M')}
- Gecikme: {delay_minutes} dakika

📍 {event.title} için:
- Orijinal varış: {event.start_time.strftime('%H:%M')}
- Tahmini varış: {new_arrival.strftime('%H:%M')}

💡 Öneriler:
1. Alternatif ulaşım (taksi/dolmuş) ile {delay_minutes - 5} dakika kazanabilirsin
2. Etkinlik sorumlusuna haber ver
3. Günün geri kalanını buna göre ayarla""",
            action_required=True,
            metadata={
                "delay_minutes": delay_minutes,
                "event_id": event.id,
                "new_arrival": new_arrival.isoformat()
            }
        )

    def check_weather_impact(
        self,
        weather_condition: str,
        temperature: float,
        travel_info: TravelInfo
    ) -> Optional[Decision]:
        """
        Check if weather conditions require schedule adjustments.
        """
        adjustments = []
        
        if "rain" in weather_condition.lower() or "yağmur" in weather_condition.lower():
            adjustments.append(f"☔ Yağmur: +{settings.rain_time_buffer}% yürüme süresi")
        
        if "snow" in weather_condition.lower() or "kar" in weather_condition.lower():
            adjustments.append(f"❄️ Kar: +{settings.snow_time_buffer}% yürüme süresi")
        
        if temperature > 35:
            adjustments.append("🌡️ Aşırı sıcak: Gölgeli güzergah önerilir, su al!")
        elif temperature < 0:
            adjustments.append("🥶 Dondurucu: Kalın giyin, yollar kaygan olabilir")
        
        if adjustments:
            return Decision(
                decision_type=DecisionType.WEATHER_WARNING,
                urgency=Urgency.MEDIUM,
                title="🌤️ Hava Durumu Uyarısı",
                message=f"{self.user_name}, bugün hava durumu planlarını etkileyebilir:\n\n" + "\n".join(adjustments),
                action_required=False,
                metadata={
                    "weather": weather_condition,
                    "temperature": temperature
                }
            )
        
        return None


# Singleton instance
decision_engine = DecisionEngine()
