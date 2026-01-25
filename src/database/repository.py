"""
ASTRAEUS - Autonomous Life Orchestrator
Database Repository Module

This module provides data access layer for database operations.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, update, delete, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
import structlog

from src.config import settings
from src.database.models import (
    Base, User, Event, SavedLocation, Reminder, 
    TravelLog, ConversationMessage, EventStatus, EventPriority
)

logger = structlog.get_logger()


class Database:
    """
    Database connection and session management.
    """
    
    def __init__(self, database_url: str = None):
        self.database_url = database_url or settings.database_url
        self.engine = None
        self.session_factory = None
    
    async def connect(self) -> None:
        """Initialize database connection."""
        self.engine = create_async_engine(
            self.database_url,
            echo=settings.log_level == "DEBUG",
            pool_size=5,
            max_overflow=10
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("Database connected", url=self.database_url.split("@")[-1])
    
    async def disconnect(self) -> None:
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database disconnected")
    
    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")
    
    def session(self) -> AsyncSession:
        """Get a new database session."""
        return self.session_factory()


class UserRepository:
    """
    Repository for User operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        result = await self.session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()
    
    async def get_or_create(self, telegram_id: int, name: str) -> User:
        """Get existing user or create new one."""
        user = await self.get_by_telegram_id(telegram_id)
        
        if not user:
            user = User(telegram_id=telegram_id, name=name)
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            logger.info("New user created", telegram_id=telegram_id, name=name)
        
        return user
    
    async def update_location(
        self,
        telegram_id: int,
        latitude: float,
        longitude: float,
        location_name: str = None
    ) -> Optional[User]:
        """Update user's current location."""
        user = await self.get_by_telegram_id(telegram_id)
        
        if user:
            user.current_latitude = latitude
            user.current_longitude = longitude
            user.current_location_name = location_name
            user.last_location_update = datetime.utcnow()
            await self.session.commit()
            logger.info("User location updated", telegram_id=telegram_id)
        
        return user
    
    async def update_preferences(
        self,
        telegram_id: int,
        **preferences
    ) -> Optional[User]:
        """Update user preferences."""
        user = await self.get_by_telegram_id(telegram_id)
        
        if user:
            for key, value in preferences.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            await self.session.commit()
            logger.info("User preferences updated", telegram_id=telegram_id)
        
        return user


class EventRepository:
    """
    Repository for Event operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: int,
        title: str,
        start_time: datetime,
        **kwargs
    ) -> Event:
        """Create a new event."""
        event = Event(
            user_id=user_id,
            title=title,
            start_time=start_time,
            **kwargs
        )
        self.session.add(event)
        await self.session.commit()
        await self.session.refresh(event)
        logger.info("Event created", title=title, start=start_time.isoformat())
        return event
    
    async def get_upcoming(
        self,
        user_id: int,
        limit: int = 10,
        hours_ahead: int = 24
    ) -> List[Event]:
        """Get upcoming events for a user."""
        now = datetime.utcnow()
        end_time = now + timedelta(hours=hours_ahead)
        
        result = await self.session.execute(
            select(Event)
            .where(
                and_(
                    Event.user_id == user_id,
                    Event.start_time >= now,
                    Event.start_time <= end_time,
                    Event.status == EventStatus.UPCOMING
                )
            )
            .order_by(Event.start_time)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_next_event(self, user_id: int) -> Optional[Event]:
        """Get the next upcoming event."""
        result = await self.session.execute(
            select(Event)
            .where(
                and_(
                    Event.user_id == user_id,
                    Event.start_time > datetime.utcnow(),
                    Event.status == EventStatus.UPCOMING
                )
            )
            .order_by(Event.start_time)
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def update_status(
        self,
        event_id: int,
        status: EventStatus
    ) -> Optional[Event]:
        """Update event status."""
        result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if event:
            event.status = status
            await self.session.commit()
            logger.info("Event status updated", event_id=event_id, status=status.value)
        
        return event
    
    async def update_travel_info(
        self,
        event_id: int,
        travel_minutes: int,
        walking_minutes: int,
        buffer_minutes: int = 0,
        transport_mode: str = None,
        transport_line: str = None
    ) -> Optional[Event]:
        """Update travel information for an event."""
        result = await self.session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if event:
            event.travel_minutes = travel_minutes
            event.walking_minutes = walking_minutes
            event.buffer_minutes = buffer_minutes
            event.transport_mode = transport_mode
            event.transport_line = transport_line
            await self.session.commit()
        
        return event
    
    async def delete(self, event_id: int) -> bool:
        """Delete an event."""
        await self.session.execute(
            delete(Event).where(Event.id == event_id)
        )
        await self.session.commit()
        logger.info("Event deleted", event_id=event_id)
        return True


class ReminderRepository:
    """
    Repository for Reminder operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(
        self,
        user_id: int,
        message: str,
        trigger_time: datetime,
        event_id: int = None,
        reminder_type: str = "general",
        job_id: str = None,
        metadata: Dict = None
    ) -> Reminder:
        """Create a new reminder."""
        reminder = Reminder(
            user_id=user_id,
            event_id=event_id,
            message=message,
            trigger_time=trigger_time,
            reminder_type=reminder_type,
            job_id=job_id,
            metadata=metadata
        )
        self.session.add(reminder)
        await self.session.commit()
        await self.session.refresh(reminder)
        logger.info("Reminder created", trigger=trigger_time.isoformat())
        return reminder
    
    async def get_pending(
        self,
        user_id: int = None,
        limit: int = 50
    ) -> List[Reminder]:
        """Get pending (unsent) reminders."""
        query = select(Reminder).where(
            and_(
                Reminder.is_sent == False,
                Reminder.trigger_time <= datetime.utcnow()
            )
        )
        
        if user_id:
            query = query.where(Reminder.user_id == user_id)
        
        result = await self.session.execute(
            query.order_by(Reminder.trigger_time).limit(limit)
        )
        return list(result.scalars().all())
    
    async def mark_sent(self, reminder_id: int) -> None:
        """Mark a reminder as sent."""
        result = await self.session.execute(
            select(Reminder).where(Reminder.id == reminder_id)
        )
        reminder = result.scalar_one_or_none()
        
        if reminder:
            reminder.is_sent = True
            reminder.sent_at = datetime.utcnow()
            await self.session.commit()
    
    async def cancel_by_job_id(self, job_id: str) -> bool:
        """Cancel a reminder by its job ID."""
        await self.session.execute(
            delete(Reminder).where(Reminder.job_id == job_id)
        )
        await self.session.commit()
        return True


class TravelLogRepository:
    """
    Repository for TravelLog operations.
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def log_travel(
        self,
        user_id: int,
        origin_coords: tuple,
        dest_coords: tuple,
        departed_at: datetime,
        estimated_duration: int,
        **kwargs
    ) -> TravelLog:
        """Log a travel entry."""
        log = TravelLog(
            user_id=user_id,
            origin_latitude=origin_coords[0],
            origin_longitude=origin_coords[1],
            destination_latitude=dest_coords[0],
            destination_longitude=dest_coords[1],
            departed_at=departed_at,
            estimated_duration=estimated_duration,
            **kwargs
        )
        self.session.add(log)
        await self.session.commit()
        await self.session.refresh(log)
        return log
    
    async def complete_travel(
        self,
        log_id: int,
        arrived_at: datetime,
        was_on_time: bool,
        delay_minutes: int = 0
    ) -> Optional[TravelLog]:
        """Complete a travel log with arrival info."""
        result = await self.session.execute(
            select(TravelLog).where(TravelLog.id == log_id)
        )
        log = result.scalar_one_or_none()
        
        if log:
            log.arrived_at = arrived_at
            log.actual_duration = int((arrived_at - log.departed_at).total_seconds() / 60)
            log.was_on_time = was_on_time
            log.delay_minutes = delay_minutes
            await self.session.commit()
        
        return log
    
    async def get_average_duration(
        self,
        user_id: int,
        origin_coords: tuple,
        dest_coords: tuple,
        radius_km: float = 0.5
    ) -> Optional[int]:
        """Get average travel duration between two points based on history."""
        # This is a simplified version - production would use proper geo queries
        result = await self.session.execute(
            select(TravelLog)
            .where(
                and_(
                    TravelLog.user_id == user_id,
                    TravelLog.actual_duration.isnot(None)
                )
            )
            .limit(10)
        )
        logs = list(result.scalars().all())
        
        if logs:
            avg = sum(log.actual_duration for log in logs) / len(logs)
            return int(avg)
        
        return None


# Singleton database instance
database = Database()
