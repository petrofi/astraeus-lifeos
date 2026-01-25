"""
ASTRAEUS - Test Suite
Location Module Tests
"""

import pytest
from src.location.gps_handler import GPSHandler, Location


class TestLocation:
    """Tests for the Location dataclass."""
    
    def test_coords_property(self):
        """Test coordinates tuple property."""
        loc = Location(
            latitude=41.0082,
            longitude=28.9784,
            name="Istanbul"
        )
        
        assert loc.coords == (41.0082, 28.9784)
    
    def test_distance_to_same_location(self):
        """Test distance to same location is zero."""
        loc1 = Location(latitude=41.0082, longitude=28.9784)
        loc2 = Location(latitude=41.0082, longitude=28.9784)
        
        distance = loc1.distance_to(loc2)
        assert distance == pytest.approx(0, abs=0.001)
    
    def test_distance_to_different_location(self):
        """Test distance calculation between two points."""
        istanbul = Location(latitude=41.0082, longitude=28.9784)
        ankara = Location(latitude=39.9334, longitude=32.8597)
        
        distance = istanbul.distance_to(ankara)
        
        # Istanbul to Ankara is approximately 350-400 km
        assert 300 < distance < 450


class TestGPSHandler:
    """Tests for the GPSHandler class."""
    
    @pytest.fixture
    def handler(self):
        """Create a GPS handler instance."""
        return GPSHandler()
    
    def test_calculate_distance(self, handler):
        """Test distance calculation."""
        # Istanbul coordinates
        lat1, lon1 = 41.0082, 28.9784
        # Taksim coordinates (about 3-4 km away)
        lat2, lon2 = 41.0370, 28.9850
        
        distance = handler.calculate_distance(lat1, lon1, lat2, lon2)
        
        # Should be about 3-4 km
        assert 2 < distance < 5
    
    def test_estimate_walking_time(self, handler):
        """Test walking time estimation."""
        distance_km = 1.0  # 1 km
        
        time = handler.estimate_walking_time(distance_km)
        
        # At 5 km/h, 1 km should take 12 minutes
        assert time == 12
    
    def test_estimate_walking_time_custom_pace(self, handler):
        """Test walking time with custom pace."""
        distance_km = 2.0  # 2 km
        
        time = handler.estimate_walking_time(distance_km, pace=4.0)
        
        # At 4 km/h, 2 km should take 30 minutes
        assert time == 30


# Note: These tests require network access
@pytest.mark.integration
class TestGPSHandlerIntegration:
    """Integration tests that require network."""
    
    @pytest.fixture
    def handler(self):
        return GPSHandler()
    
    @pytest.mark.asyncio
    async def test_reverse_geocode_istanbul(self, handler):
        """Test reverse geocoding for Istanbul coordinates."""
        location = await handler.reverse_geocode(41.0082, 28.9784)
        
        assert location is not None
        assert location.latitude == 41.0082
        assert location.longitude == 28.9784
        # Should contain Istanbul or Turkey in address
        if location.address:
            assert "istanbul" in location.address.lower() or "türkiye" in location.address.lower()
    
    @pytest.mark.asyncio
    async def test_geocode_istanbul(self, handler):
        """Test geocoding for Istanbul."""
        location = await handler.geocode("İstanbul, Türkiye")
        
        assert location is not None
        # Istanbul is roughly at 41°N, 29°E
        assert 40 < location.latitude < 42
        assert 28 < location.longitude < 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
