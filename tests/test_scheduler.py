"""
ASTRAEUS - Test Suite
Time Calculator Tests
"""

import pytest
from datetime import datetime, timedelta
from src.scheduler.time_calculator import TimeCalculator, TimeCalculation


class TestTimeCalculator:
    """Tests for the TimeCalculator class."""
    
    @pytest.fixture
    def calculator(self):
        """Create a calculator instance with 5 min default prep time."""
        return TimeCalculator(default_prep_time=5)
    
    def test_basic_departure_calculation(self, calculator):
        """Test basic departure time calculation."""
        event_time = datetime(2026, 1, 25, 20, 0, 0)  # 20:00
        
        result = calculator.calculate_departure(
            event_time=event_time,
            travel_minutes=30,
            walking_minutes=10,
            prep_minutes=5,
            buffer_minutes=0
        )
        
        # 20:00 - (30 + 10 + 5) = 19:15
        expected_departure = datetime(2026, 1, 25, 19, 15, 0)
        assert result.departure_time == expected_departure
        assert result.total_duration == timedelta(minutes=45)
    
    def test_departure_with_buffer(self, calculator):
        """Test departure calculation with weather buffer."""
        event_time = datetime(2026, 1, 25, 20, 0, 0)
        
        result = calculator.calculate_departure(
            event_time=event_time,
            travel_minutes=30,
            walking_minutes=10,
            buffer_minutes=10  # Extra buffer for rain
        )
        
        # 20:00 - (30 + 10 + 5 + 10) = 19:05
        expected_departure = datetime(2026, 1, 25, 19, 5, 0)
        assert result.departure_time == expected_departure
    
    def test_weather_adjusted_calculation(self, calculator):
        """Test weather-adjusted departure time."""
        event_time = datetime(2026, 1, 25, 20, 0, 0)
        
        result = calculator.calculate_with_weather(
            event_time=event_time,
            travel_minutes=30,
            walking_minutes=10,
            weather_condition="rain",
            is_raining=True
        )
        
        # Should add at least 5 minutes buffer for rain
        assert result.buffer_time >= timedelta(minutes=5)
        
        # Departure should be earlier than without weather
        no_weather = calculator.calculate_departure(
            event_time=event_time,
            travel_minutes=30,
            walking_minutes=10
        )
        assert result.departure_time < no_weather.departure_time
    
    def test_time_until_departure_future(self, calculator):
        """Test time remaining calculation for future departure."""
        future_departure = datetime.now() + timedelta(hours=2)
        
        remaining, formatted = calculator.time_until_departure(future_departure)
        
        assert remaining > timedelta(0)
        assert "saat" in formatted or "dakika" in formatted
    
    def test_time_until_departure_past(self, calculator):
        """Test time remaining calculation for past departure."""
        past_departure = datetime.now() - timedelta(minutes=30)
        
        remaining, formatted = calculator.time_until_departure(past_departure)
        
        assert remaining < timedelta(0)
        assert "geç" in formatted
    
    def test_countdown_formatting_critical(self, calculator):
        """Test countdown message for critical timing."""
        departure = datetime.now() + timedelta(minutes=3)
        countdown = calculator.format_countdown(departure)
        
        assert "HEMEN ÇIK" in countdown or "🔴" in countdown
    
    def test_countdown_formatting_warning(self, calculator):
        """Test countdown message for warning timing."""
        departure = datetime.now() + timedelta(minutes=12)
        countdown = calculator.format_countdown(departure)
        
        assert "Hazırlan" in countdown or "🟡" in countdown
    
    def test_countdown_formatting_safe(self, calculator):
        """Test countdown message for safe timing."""
        departure = datetime.now() + timedelta(minutes=25)
        countdown = calculator.format_countdown(departure)
        
        assert "🟢" in countdown or "sonra" in countdown
    
    def test_latest_departure_no_prep(self, calculator):
        """Test latest possible departure (no prep time)."""
        event_time = datetime(2026, 1, 25, 20, 0, 0)
        
        latest = calculator.calculate_latest_departure(
            event_time=event_time,
            travel_minutes=30,
            walking_minutes=10
        )
        
        # 20:00 - (30 + 10) = 19:20 (no prep time)
        expected = datetime(2026, 1, 25, 19, 20, 0)
        assert latest == expected


class TestTimeCalculation:
    """Tests for the TimeCalculation dataclass."""
    
    def test_is_urgent_true(self):
        """Test urgent detection when close to departure."""
        calc = TimeCalculation(
            event_time=datetime.now() + timedelta(minutes=30),
            departure_time=datetime.now() + timedelta(minutes=10),
            travel_duration=timedelta(minutes=15),
            walking_duration=timedelta(minutes=5),
            prep_time=timedelta(minutes=5),
            buffer_time=timedelta(minutes=5),
            total_duration=timedelta(minutes=30)
        )
        
        assert calc.is_urgent is True
    
    def test_is_urgent_false(self):
        """Test urgent detection when far from departure."""
        calc = TimeCalculation(
            event_time=datetime.now() + timedelta(hours=2),
            departure_time=datetime.now() + timedelta(hours=1),
            travel_duration=timedelta(minutes=30),
            walking_duration=timedelta(minutes=10),
            prep_time=timedelta(minutes=5),
            buffer_time=timedelta(minutes=15),
            total_duration=timedelta(hours=1)
        )
        
        assert calc.is_urgent is False
    
    def test_is_overdue(self):
        """Test overdue detection."""
        calc = TimeCalculation(
            event_time=datetime.now() - timedelta(minutes=10),
            departure_time=datetime.now() - timedelta(minutes=40),
            travel_duration=timedelta(minutes=20),
            walking_duration=timedelta(minutes=5),
            prep_time=timedelta(minutes=5),
            buffer_time=timedelta(minutes=0),
            total_duration=timedelta(minutes=30)
        )
        
        assert calc.is_overdue is True
    
    def test_format_summary(self):
        """Test summary formatting."""
        calc = TimeCalculation(
            event_time=datetime(2026, 1, 25, 20, 0, 0),
            departure_time=datetime(2026, 1, 25, 19, 15, 0),
            travel_duration=timedelta(minutes=30),
            walking_duration=timedelta(minutes=10),
            prep_time=timedelta(minutes=5),
            buffer_time=timedelta(minutes=0),
            total_duration=timedelta(minutes=45)
        )
        
        summary = calc.format_summary()
        
        assert "20:00" in summary  # Event time
        assert "19:15" in summary  # Departure time
        assert "30" in summary  # Travel minutes
        assert "Toplam: 45" in summary  # Total


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
