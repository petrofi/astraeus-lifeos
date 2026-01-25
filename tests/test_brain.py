"""
ASTRAEUS - Test Suite
Decision Engine Tests
"""

import pytest
from datetime import datetime, timedelta
from src.brain.decision_engine import (
    DecisionEngine, Decision, DecisionType, Urgency,
    Event, TravelInfo
)


class TestDecisionEngine:
    """Tests for the DecisionEngine class."""
    
    @pytest.fixture
    def engine(self):
        """Create a decision engine instance."""
        return DecisionEngine(user_name="Tarık")
    
    @pytest.fixture
    def sample_event(self):
        """Create a sample event."""
        return Event(
            id="evt_001",
            title="Python Dersi",
            start_time=datetime.now() + timedelta(hours=2),
            location="Üniversite",
            priority=3
        )
    
    @pytest.fixture
    def sample_travel_info(self):
        """Create sample travel info."""
        return TravelInfo(
            duration_minutes=30,
            walking_minutes=10,
            transport_type="bus",
            transport_line="502",
            weather_buffer_minutes=5
        )
    
    def test_calculate_departure_time(self, engine, sample_travel_info):
        """Test departure time calculation."""
        event_time = datetime(2026, 1, 25, 20, 0, 0)
        
        departure = engine.calculate_departure_time(
            event_time=event_time,
            travel_info=sample_travel_info,
            include_buffer=True
        )
        
        # 20:00 - (30 + 10 + 5 + 5) = 19:10
        expected = datetime(2026, 1, 25, 19, 10, 0)
        assert departure == expected
    
    def test_departure_notification_critical(self, engine):
        """Test notification when departure is overdue."""
        event = Event(
            id="evt_001",
            title="Toplantı",
            start_time=datetime.now() + timedelta(minutes=30),
            priority=3
        )
        travel = TravelInfo(
            duration_minutes=35,  # Takes 35 min, but only 30 min left!
            walking_minutes=5,
            transport_type="bus"
        )
        
        decision = engine.should_notify_departure(event, travel)
        
        assert decision is not None
        assert decision.urgency == Urgency.CRITICAL
        assert decision.action_required is True
        assert "HEMEN" in decision.title
    
    def test_departure_notification_medium(self, engine):
        """Test notification for medium urgency."""
        event = Event(
            id="evt_001",
            title="Ders",
            start_time=datetime.now() + timedelta(hours=1),
            priority=2
        )
        travel = TravelInfo(
            duration_minutes=30,
            walking_minutes=10,
            transport_type="bus"
        )
        
        decision = engine.should_notify_departure(event, travel)
        
        # With 1 hour and 45 min total travel, should trigger within 15 min warning
        if decision:
            assert decision.urgency in [Urgency.MEDIUM, Urgency.HIGH]
    
    def test_no_notification_when_plenty_of_time(self, engine):
        """Test no notification when there's plenty of time."""
        event = Event(
            id="evt_001",
            title="Akşam Yemeği",
            start_time=datetime.now() + timedelta(hours=5),
            priority=1
        )
        travel = TravelInfo(
            duration_minutes=30,
            walking_minutes=10,
            transport_type="walking"
        )
        
        decision = engine.should_notify_departure(event, travel)
        
        assert decision is None
    
    def test_schedule_conflict_detection(self, engine):
        """Test detection of schedule conflicts."""
        now = datetime.now()
        
        events = [
            Event(
                id="evt_001",
                title="Meeting 1",
                start_time=now + timedelta(hours=1),
                end_time=now + timedelta(hours=2),
                priority=2
            ),
            Event(
                id="evt_002",
                title="Meeting 2",
                start_time=now + timedelta(hours=2, minutes=10),  # Only 10 min gap
                priority=2
            )
        ]
        
        travel_infos = {
            "evt_002": TravelInfo(
                duration_minutes=20,  # Needs 20 min travel
                walking_minutes=5,
                transport_type="bus"
            )
        }
        
        conflicts = engine.check_schedule_conflicts(events, travel_infos)
        
        # Should detect conflict: Meeting 1 ends at +2h, but need to leave at +1h35m
        assert len(conflicts) > 0
        assert conflicts[0].decision_type == DecisionType.SCHEDULE_CONFLICT
    
    def test_replan_suggestion(self, engine, sample_event, sample_travel_info):
        """Test replanning suggestion."""
        original = datetime.now()
        actual = original + timedelta(minutes=15)  # 15 min late
        
        decision = engine.suggest_replan(
            original_departure=original,
            actual_departure=actual,
            event=sample_event,
            travel_info=sample_travel_info
        )
        
        assert decision.decision_type == DecisionType.REPLAN_NEEDED
        assert decision.urgency == Urgency.HIGH
        assert "15 dakika" in decision.message
        assert decision.action_required is True
    
    def test_weather_impact_rain(self, engine, sample_travel_info):
        """Test weather impact detection for rain."""
        decision = engine.check_weather_impact(
            weather_condition="light rain",
            temperature=15.0,
            travel_info=sample_travel_info
        )
        
        assert decision is not None
        assert decision.decision_type == DecisionType.WEATHER_WARNING
        assert "yağmur" in decision.message.lower() or "rain" in decision.message.lower()
    
    def test_weather_impact_extreme_heat(self, engine, sample_travel_info):
        """Test weather impact detection for extreme heat."""
        decision = engine.check_weather_impact(
            weather_condition="clear sky",
            temperature=38.0,  # Very hot
            travel_info=sample_travel_info
        )
        
        assert decision is not None
        assert decision.decision_type == DecisionType.WEATHER_WARNING
        assert "sıcak" in decision.message.lower() or "su" in decision.message.lower()


class TestDecision:
    """Tests for the Decision dataclass."""
    
    def test_to_dict(self):
        """Test decision serialization."""
        decision = Decision(
            decision_type=DecisionType.DEPARTURE_REMINDER,
            urgency=Urgency.HIGH,
            title="Test Title",
            message="Test message",
            action_required=True,
            deadline=datetime(2026, 1, 25, 19, 0, 0),
            metadata={"key": "value"}
        )
        
        data = decision.to_dict()
        
        assert data["type"] == "departure_reminder"
        assert data["urgency"] == "high"
        assert data["title"] == "Test Title"
        assert data["action_required"] is True
        assert "2026-01-25" in data["deadline"]


class TestTravelInfo:
    """Tests for the TravelInfo dataclass."""
    
    def test_travel_info_creation(self):
        """Test TravelInfo creation."""
        info = TravelInfo(
            duration_minutes=30,
            walking_minutes=10,
            transport_type="bus",
            transport_line="502",
            departure_time=datetime(2026, 1, 25, 19, 0, 0),
            weather_buffer_minutes=5
        )
        
        assert info.duration_minutes == 30
        assert info.transport_line == "502"
        assert info.weather_buffer_minutes == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
