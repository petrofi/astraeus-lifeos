"""
ASTRAEUS - Autonomous Life Orchestrator
Context Manager Module

This module manages conversation context and user state
for maintaining coherent, contextual AI interactions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from collections import deque
import json
import structlog

logger = structlog.get_logger()


@dataclass
class Message:
    """Represents a single message in the conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary for serialization."""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class UserState:
    """Represents the current state of the user."""
    current_location: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    last_location_update: Optional[datetime] = None
    
    current_activity: Optional[str] = None
    energy_level: Optional[str] = None  # "high", "medium", "low"
    
    # Preferences learned over time
    preferred_transport: str = "bus"
    morning_person: bool = False
    typical_prep_time: int = 10  # minutes


@dataclass
class ContextWindow:
    """
    Manages the conversation context window.
    Keeps track of recent messages and user state for context-aware responses.
    """
    user_id: int
    max_messages: int = 20
    messages: deque = field(default_factory=lambda: deque(maxlen=20))
    user_state: UserState = field(default_factory=UserState)
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a message to the context window."""
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        self.messages.append(message)
        self.last_updated = datetime.now()
        logger.debug("Message added to context", role=role, user_id=self.user_id)
    
    def add_user_message(self, content: str, metadata: Optional[Dict] = None) -> None:
        """Add a user message."""
        self.add_message("user", content, metadata)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None) -> None:
        """Add an assistant message."""
        self.add_message("assistant", content, metadata)
    
    def update_location(
        self,
        location_name: str,
        latitude: float,
        longitude: float
    ) -> None:
        """Update user's current location."""
        self.user_state.current_location = location_name
        self.user_state.latitude = latitude
        self.user_state.longitude = longitude
        self.user_state.last_location_update = datetime.now()
        logger.info("Location updated", location=location_name, user_id=self.user_id)
    
    def get_conversation_history(self, limit: Optional[int] = None) -> List[Dict]:
        """Get recent conversation history as list of dicts."""
        messages = list(self.messages)
        if limit:
            messages = messages[-limit:]
        return [msg.to_dict() for msg in messages]
    
    def get_context_summary(self) -> str:
        """Generate a summary of current context for the AI."""
        summary_parts = []
        
        # Location context
        if self.user_state.current_location:
            time_since = ""
            if self.user_state.last_location_update:
                delta = datetime.now() - self.user_state.last_location_update
                minutes = int(delta.total_seconds() / 60)
                if minutes < 60:
                    time_since = f" ({minutes} dakika önce güncellendi)"
                else:
                    hours = minutes // 60
                    time_since = f" ({hours} saat önce güncellendi)"
            summary_parts.append(f"📍 Konum: {self.user_state.current_location}{time_since}")
        
        # Activity context
        if self.user_state.current_activity:
            summary_parts.append(f"🎯 Aktivite: {self.user_state.current_activity}")
        
        # Energy level
        if self.user_state.energy_level:
            energy_emoji = {"high": "⚡", "medium": "🔋", "low": "🪫"}.get(
                self.user_state.energy_level, "🔋"
            )
            summary_parts.append(f"{energy_emoji} Enerji: {self.user_state.energy_level}")
        
        # Recent conversation summary
        if self.messages:
            recent_count = min(len(self.messages), 5)
            summary_parts.append(f"💬 Son {recent_count} mesaj bağlamda")
        
        return "\n".join(summary_parts) if summary_parts else "Bağlam bilgisi yok"
    
    def clear(self) -> None:
        """Clear all messages but keep user state."""
        self.messages.clear()
        logger.info("Context cleared", user_id=self.user_id)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "user_id": self.user_id,
            "messages": [msg.to_dict() for msg in self.messages],
            "user_state": {
                "current_location": self.user_state.current_location,
                "latitude": self.user_state.latitude,
                "longitude": self.user_state.longitude,
                "current_activity": self.user_state.current_activity,
                "energy_level": self.user_state.energy_level
            },
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat()
        }


class ContextManager:
    """
    Manages context windows for multiple users.
    Provides a centralized way to access and update user contexts.
    """
    
    def __init__(self, max_messages_per_user: int = 20):
        self.contexts: Dict[int, ContextWindow] = {}
        self.max_messages = max_messages_per_user
        logger.info("Context manager initialized", max_messages=max_messages_per_user)
    
    def get_context(self, user_id: int) -> ContextWindow:
        """Get or create a context window for a user."""
        if user_id not in self.contexts:
            self.contexts[user_id] = ContextWindow(
                user_id=user_id,
                max_messages=self.max_messages
            )
            logger.info("New context created", user_id=user_id)
        return self.contexts[user_id]
    
    def clear_context(self, user_id: int) -> None:
        """Clear context for a specific user."""
        if user_id in self.contexts:
            self.contexts[user_id].clear()
    
    def remove_context(self, user_id: int) -> None:
        """Remove context entirely for a user."""
        if user_id in self.contexts:
            del self.contexts[user_id]
            logger.info("Context removed", user_id=user_id)
    
    def get_all_active_users(self) -> List[int]:
        """Get list of all users with active contexts."""
        return list(self.contexts.keys())
    
    def export_all_contexts(self) -> Dict[int, Dict]:
        """Export all contexts for persistence."""
        return {
            user_id: ctx.to_dict()
            for user_id, ctx in self.contexts.items()
        }


# Global context manager instance
context_manager = ContextManager()
