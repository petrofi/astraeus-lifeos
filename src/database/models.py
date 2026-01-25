"""
ASTRAEUS - Autonomous Life Orchestrator
Database Models Module

This module defines SQLAlchemy models for data persistence.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, 
    ForeignKey, Text, Enum as SQLEnum, JSON
)
from sqlalchemy.orm import relationship, DeclarativeBase
from sqlalchemy.ext.asyncio import AsyncAttrs
import enum


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""
    pass


class EventPriority(enum.Enum):
    """Priority levels for events."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4
    UNMISSABLE = 5


class EventStatus(enum.Enum):
    """Status of an event."""
    UPCOMING = "upcoming"
    IN_TRANSIT = "in_transit"
    ONGOING = "ongoing"
    COMPLETED = "completed"
    MISSED = "missed"
    CANCELLED = "cancelled"


class User(Base):
    """User model for storing user preferences and data."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Preferences
    timezone = Column(String(50), default="Europe/Istanbul")
    default_prep_time = Column(Integer, default=5)  # Minutes
    preferred_transport = Column(String(20), default="bus")
    morning_person = Column(Boolean, default=False)
    
    # Default locations
    home_latitude = Column(Float, nullable=True)
    home_longitude = Column(Float, nullable=True)
    home_address = Column(String(500), nullable=True)
    
    work_latitude = Column(Float, nullable=True)
    work_longitude = Column(Float, nullable=True)
    work_address = Column(String(500), nullable=True)
    
    # Current state
    current_latitude = Column(Float, nullable=True)
    current_longitude = Column(Float, nullable=True)
    current_location_name = Column(String(500), nullable=True)
    last_location_update = Column(DateTime, nullable=True)
    
    # Relationships
    events = relationship("Event", back_populates="user", cascade="all, delete-orphan")
    locations = relationship("SavedLocation", back_populates="user", cascade="all, delete-orphan")
    reminders = relationship("Reminder", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, telegram_id={self.telegram_id})>"


class Event(Base):
    """Event model for scheduled activities."""
    
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    
    # Location
    location_name = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Travel info
    travel_minutes = Column(Integer, default=0)
    walking_minutes = Column(Integer, default=0)
    buffer_minutes = Column(Integer, default=0)
    transport_mode = Column(String(20), nullable=True)
    transport_line = Column(String(50), nullable=True)
    
    # Meta
    priority = Column(SQLEnum(EventPriority), default=EventPriority.NORMAL)
    status = Column(SQLEnum(EventStatus), default=EventStatus.UPCOMING)
    
    # Recurrence
    is_recurring = Column(Boolean, default=False)
    recurrence_rule = Column(String(200), nullable=True)  # RRULE format
    
    # External calendar integration
    external_id = Column(String(200), nullable=True)  # Google/Outlook calendar ID
    calendar_source = Column(String(50), nullable=True)  # "google", "outlook"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="events")
    
    def __repr__(self):
        return f"<Event(id={self.id}, title={self.title}, start={self.start_time})>"


class SavedLocation(Base):
    """Saved locations for quick access."""
    
    __tablename__ = "saved_locations"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    address = Column(String(500), nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Categorization
    category = Column(String(50), nullable=True)  # "home", "work", "school", "cafe", etc.
    icon = Column(String(10), nullable=True)  # Emoji
    
    # Cached transit info
    nearest_bus_stop = Column(String(200), nullable=True)
    nearest_metro_station = Column(String(200), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="locations")
    
    def __repr__(self):
        return f"<SavedLocation(id={self.id}, name={self.name})>"


class Reminder(Base):
    """Scheduled reminders and notifications."""
    
    __tablename__ = "reminders"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    
    message = Column(Text, nullable=False)
    trigger_time = Column(DateTime, nullable=False, index=True)
    
    # Type
    reminder_type = Column(String(50), default="general")  # "departure", "event", "general"
    
    # Status
    is_sent = Column(Boolean, default=False)
    sent_at = Column(DateTime, nullable=True)
    
    # Meta
    job_id = Column(String(100), nullable=True)  # For cancellation
    metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="reminders")
    
    def __repr__(self):
        return f"<Reminder(id={self.id}, trigger={self.trigger_time})>"


class TravelLog(Base):
    """Log of past travels for learning patterns."""
    
    __tablename__ = "travel_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    
    # Journey details
    origin_name = Column(String(500), nullable=True)
    origin_latitude = Column(Float, nullable=False)
    origin_longitude = Column(Float, nullable=False)
    
    destination_name = Column(String(500), nullable=True)
    destination_latitude = Column(Float, nullable=False)
    destination_longitude = Column(Float, nullable=False)
    
    # Times
    departed_at = Column(DateTime, nullable=False)
    arrived_at = Column(DateTime, nullable=True)
    
    # Estimates vs actuals
    estimated_duration = Column(Integer, nullable=True)  # Minutes
    actual_duration = Column(Integer, nullable=True)  # Minutes
    
    # Transport
    transport_mode = Column(String(20), nullable=True)
    transport_line = Column(String(50), nullable=True)
    
    # Conditions
    weather_condition = Column(String(50), nullable=True)
    was_raining = Column(Boolean, default=False)
    was_rush_hour = Column(Boolean, default=False)
    
    # Outcome
    was_on_time = Column(Boolean, nullable=True)
    delay_minutes = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<TravelLog(id={self.id}, departed={self.departed_at})>"


class ConversationMessage(Base):
    """Store conversation history for context."""
    
    __tablename__ = "conversation_messages"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    
    # Context at time of message
    location_name = Column(String(500), nullable=True)
    weather_condition = Column(String(50), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role})>"
