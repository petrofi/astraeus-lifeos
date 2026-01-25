"""
ASTRAEUS - Autonomous Life Orchestrator
Dynamic Planner Module

This module handles dynamic replanning when delays or unexpected
changes occur in the user's schedule.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import structlog

from src.config import settings
from src.scheduler.time_calculator import time_calculator, TimeCalculation

logger = structlog.get_logger()


class EventPriority(Enum):
    """Priority levels for events."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    UNMISSABLE = 5


class EventStatus(Enum):
    """Status of an event."""
    UPCOMING = "upcoming"
    IN_TRANSIT = "in_transit"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


@dataclass
class ScheduledEvent:
    """Represents a scheduled event in the user's day."""
    id: str
    title: str
    start_time: datetime
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    location_coords: Optional[tuple] = None
    priority: EventPriority = EventPriority.NORMAL
    status: EventStatus = EventStatus.UPCOMING
    notes: Optional[str] = None
    travel_minutes: int = 0
    walking_minutes: int = 0
    buffer_minutes: int = 0
    
    @property
    def duration(self) -> timedelta:
        """Get event duration."""
        if self.end_time:
            return self.end_time - self.start_time
        return timedelta(hours=1)  # Default 1 hour
    
    def get_departure_time(self, buffer: int = 0) -> datetime:
        """Calculate departure time for this event."""
        calc = time_calculator.calculate_departure(
            event_time=self.start_time,
            travel_minutes=self.travel_minutes,
            walking_minutes=self.walking_minutes,
            buffer_minutes=self.buffer_minutes + buffer
        )
        return calc.departure_time


@dataclass
class DayPlan:
    """Represents the full schedule for a day."""
    date: datetime
    events: List[ScheduledEvent] = field(default_factory=list)
    wake_time: Optional[datetime] = None
    sleep_time: Optional[datetime] = None
    
    def __post_init__(self):
        self.events.sort(key=lambda e: e.start_time)
    
    def add_event(self, event: ScheduledEvent) -> None:
        """Add an event and keep list sorted."""
        self.events.append(event)
        self.events.sort(key=lambda e: e.start_time)
    
    def get_next_event(self, after: datetime = None) -> Optional[ScheduledEvent]:
        """Get the next upcoming event."""
        after = after or datetime.now()
        for event in self.events:
            if event.start_time > after and event.status == EventStatus.UPCOMING:
                return event
        return None
    
    def get_active_events(self) -> List[ScheduledEvent]:
        """Get all upcoming and ongoing events."""
        return [
            e for e in self.events
            if e.status in (EventStatus.UPCOMING, EventStatus.ONGOING, EventStatus.IN_TRANSIT)
        ]


@dataclass 
class ReplanResult:
    """Result of a replanning operation."""
    success: bool
    message: str
    original_plan: DayPlan
    new_plan: DayPlan
    affected_events: List[ScheduledEvent]
    delay_minutes: int
    suggestions: List[str]


class DynamicPlanner:
    """
    Handles dynamic schedule replanning when delays occur.
    """
    
    def __init__(self, user_name: str = None):
        self.user_name = user_name or settings.user_name
        self.current_plan: Optional[DayPlan] = None
        logger.info("Dynamic planner initialized", user=self.user_name)
    
    def create_day_plan(
        self,
        date: datetime = None,
        wake_time: datetime = None,
        sleep_time: datetime = None
    ) -> DayPlan:
        """Create a new day plan."""
        date = date or datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        plan = DayPlan(
            date=date,
            wake_time=wake_time,
            sleep_time=sleep_time
        )
        self.current_plan = plan
        return plan
    
    def add_event_to_plan(
        self,
        plan: DayPlan,
        title: str,
        start_time: datetime,
        end_time: datetime = None,
        location: str = None,
        priority: EventPriority = EventPriority.NORMAL,
        travel_minutes: int = 0,
        walking_minutes: int = 0
    ) -> ScheduledEvent:
        """Add an event to a day plan."""
        event = ScheduledEvent(
            id=f"evt_{len(plan.events)}_{start_time.strftime('%H%M')}",
            title=title,
            start_time=start_time,
            end_time=end_time,
            location=location,
            priority=priority,
            travel_minutes=travel_minutes,
            walking_minutes=walking_minutes
        )
        plan.add_event(event)
        logger.info("Event added", title=title, time=start_time.isoformat())
        return event
    
    def check_conflicts(self, plan: DayPlan) -> List[Dict[str, Any]]:
        """
        Check for schedule conflicts in the plan.
        
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        for i in range(len(plan.events) - 1):
            current = plan.events[i]
            next_event = plan.events[i + 1]
            
            current_end = current.end_time or (current.start_time + current.duration)
            next_departure = next_event.get_departure_time()
            
            if current_end > next_departure:
                overlap = current_end - next_departure
                conflicts.append({
                    "type": "overlap",
                    "event1": current.title,
                    "event2": next_event.title,
                    "overlap_minutes": int(overlap.total_seconds() / 60),
                    "message": f"'{current.title}' bitmeden '{next_event.title}' için çıkman gerekiyor"
                })
            elif (next_departure - current_end) < timedelta(minutes=10):
                conflicts.append({
                    "type": "tight",
                    "event1": current.title,
                    "event2": next_event.title,
                    "gap_minutes": int((next_departure - current_end).total_seconds() / 60),
                    "message": f"'{current.title}' ve '{next_event.title}' arası çok kısa"
                })
        
        return conflicts
    
    def replan_after_delay(
        self,
        plan: DayPlan,
        delay_minutes: int,
        delay_cause: str = "Bilinmeyen"
    ) -> ReplanResult:
        """
        Replan the day after a delay occurs.
        
        Args:
            plan: Current day plan
            delay_minutes: How many minutes delayed
            delay_cause: Reason for the delay
        
        Returns:
            ReplanResult with new plan and suggestions
        """
        if not plan.events:
            return ReplanResult(
                success=True,
                message="Planlanmış etkinlik yok",
                original_plan=plan,
                new_plan=plan,
                affected_events=[],
                delay_minutes=delay_minutes,
                suggestions=[]
            )
        
        delay = timedelta(minutes=delay_minutes)
        now = datetime.now()
        
        # Find affected events
        affected = []
        for event in plan.events:
            if event.status == EventStatus.UPCOMING:
                original_departure = event.get_departure_time()
                if original_departure < now + delay:
                    affected.append(event)
        
        # Generate suggestions
        suggestions = self._generate_suggestions(affected, delay_minutes)
        
        # Create new plan with adjustments
        new_plan = DayPlan(
            date=plan.date,
            events=plan.events.copy(),
            wake_time=plan.wake_time,
            sleep_time=plan.sleep_time
        )
        
        # Adjust buffer times for affected events
        for event in new_plan.events:
            if event in affected:
                # Reduce buffer but don't go negative
                event.buffer_minutes = max(0, event.buffer_minutes - delay_minutes // 2)
        
        message = self._format_replan_message(delay_minutes, delay_cause, affected, suggestions)
        
        return ReplanResult(
            success=len(affected) < len(plan.events),
            message=message,
            original_plan=plan,
            new_plan=new_plan,
            affected_events=affected,
            delay_minutes=delay_minutes,
            suggestions=suggestions
        )
    
    def _generate_suggestions(
        self,
        affected_events: List[ScheduledEvent],
        delay_minutes: int
    ) -> List[str]:
        """Generate suggestions for handling the delay."""
        suggestions = []
        
        if delay_minutes <= 5:
            suggestions.append("🏃 Hızlı yürüyerek zamanı telafi edebilirsin")
        elif delay_minutes <= 15:
            suggestions.append("🚌 Bir sonraki toplu taşıma aracını bekle")
            suggestions.append("🚕 Taksi ile zamanı telafi edebilirsin")
        else:
            suggestions.append("📱 Etkinlik sorumlusuna geç kalacağını bildir")
            suggestions.append("🚕 Taksi kullanmayı düşün")
        
        # Priority-based suggestions
        for event in affected_events:
            if event.priority == EventPriority.UNMISSABLE:
                suggestions.insert(0, f"⚠️ '{event.title}' kaçırılamaz! Hemen hareket et")
            elif event.priority == EventPriority.CRITICAL:
                suggestions.append(f"🔴 '{event.title}' önemli, erteleme istemeyi düşün")
        
        # If significant delay, suggest rescheduling
        if delay_minutes > 30:
            suggestions.append("📅 Bugünün geri kalanını yeniden planlamak ister misin?")
        
        return suggestions
    
    def _format_replan_message(
        self,
        delay_minutes: int,
        cause: str,
        affected: List[ScheduledEvent],
        suggestions: List[str]
    ) -> str:
        """Format the replan result message."""
        parts = [
            f"🔄 **Plan Güncellemesi**",
            f"",
            f"⏱️ Gecikme: {delay_minutes} dakika",
            f"📝 Sebep: {cause}",
            f""
        ]
        
        if affected:
            parts.append(f"⚠️ Etkilenen etkinlikler ({len(affected)}):")
            for event in affected[:5]:  # Show max 5
                parts.append(f"  • {event.title} ({event.start_time.strftime('%H:%M')})")
        else:
            parts.append("✅ Hiçbir etkinlik etkilenmedi")
        
        if suggestions:
            parts.append("")
            parts.append("💡 Öneriler:")
            for suggestion in suggestions[:4]:  # Show max 4
                parts.append(f"  {suggestion}")
        
        return "\n".join(parts)
    
    def estimate_recovery_time(
        self,
        plan: DayPlan,
        delay_minutes: int
    ) -> Optional[datetime]:
        """
        Estimate when the schedule can get back on track.
        
        Returns:
            Datetime when schedule normalizes, or None if not recoverable
        """
        now = datetime.now()
        accumulated_delay = delay_minutes
        
        for event in plan.events:
            if event.start_time > now:
                # Check if we can absorb delay with buffer
                if event.buffer_minutes >= accumulated_delay:
                    return event.end_time or (event.start_time + event.duration)
                else:
                    accumulated_delay -= event.buffer_minutes
        
        # If we get here, today's schedule won't recover
        # Return tomorrow morning
        tomorrow = now.replace(hour=8, minute=0, second=0) + timedelta(days=1)
        return tomorrow


# Singleton instance
dynamic_planner = DynamicPlanner()
