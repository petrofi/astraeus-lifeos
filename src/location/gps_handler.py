"""
ASTRAEUS - Autonomous Life Orchestrator
GPS Handler Module

This module handles GPS coordinate processing, geocoding,
and reverse geocoding for location-based services.
"""

from dataclasses import dataclass
from typing import Optional, Tuple, List
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import asyncio
import structlog

from src.config import settings

logger = structlog.get_logger()


@dataclass
class Location:
    """Represents a geographic location."""
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    
    @property
    def coords(self) -> Tuple[float, float]:
        """Return coordinates as tuple."""
        return (self.latitude, self.longitude)
    
    def distance_to(self, other: "Location") -> float:
        """Calculate distance to another location in kilometers."""
        return geodesic(self.coords, other.coords).kilometers
    
    def distance_to_coords(self, lat: float, lon: float) -> float:
        """Calculate distance to coordinates in kilometers."""
        return geodesic(self.coords, (lat, lon)).kilometers


class GPSHandler:
    """
    Handles GPS coordinate processing and geocoding operations.
    Uses OpenStreetMap Nominatim for free geocoding.
    """
    
    def __init__(self, user_agent: str = "astraeus-bot"):
        self.geocoder = Nominatim(user_agent=user_agent)
        self.cache = {}  # Simple cache for geocoding results
        logger.info("GPS handler initialized")
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[Location]:
        """
        Convert coordinates to a human-readable address.
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
        
        Returns:
            Location object with address details
        """
        cache_key = f"{latitude:.6f},{longitude:.6f}"
        
        if cache_key in self.cache:
            logger.debug("Cache hit for reverse geocode", coords=cache_key)
            return self.cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.geocoder.reverse(
                    f"{latitude}, {longitude}",
                    language="tr"
                )
            )
            
            if result:
                address = result.raw.get("address", {})
                location = Location(
                    latitude=latitude,
                    longitude=longitude,
                    name=result.raw.get("name"),
                    address=result.address,
                    city=address.get("city") or address.get("town") or address.get("county"),
                    country=address.get("country")
                )
                self.cache[cache_key] = location
                logger.info("Reverse geocoded", location=location.address)
                return location
            
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logger.warning("Geocoding service error", error=str(e))
        except Exception as e:
            logger.error("Reverse geocoding failed", error=str(e))
        
        return Location(latitude=latitude, longitude=longitude)
    
    async def geocode(self, address: str) -> Optional[Location]:
        """
        Convert an address to coordinates.
        
        Args:
            address: Human-readable address
        
        Returns:
            Location object with coordinates
        """
        cache_key = f"addr:{address.lower()}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self.geocoder.geocode(address, language="tr")
            )
            
            if result:
                location = Location(
                    latitude=result.latitude,
                    longitude=result.longitude,
                    name=address,
                    address=result.address
                )
                self.cache[cache_key] = location
                logger.info("Geocoded address", address=address, coords=location.coords)
                return location
            
        except (GeocoderTimedOut, GeocoderUnavailable) as e:
            logger.warning("Geocoding service error", error=str(e))
        except Exception as e:
            logger.error("Geocoding failed", error=str(e))
        
        return None
    
    async def search_nearby(
        self,
        latitude: float,
        longitude: float,
        query: str,
        radius_km: float = 1.0
    ) -> List[Location]:
        """
        Search for places near a location.
        
        Note: This uses Nominatim search which has limited nearby search.
        For production, consider using Overpass API or Google Places.
        """
        try:
            loop = asyncio.get_event_loop()
            # Add city context for better results
            search_query = f"{query}, {settings.default_city}, {settings.default_country}"
            
            results = await loop.run_in_executor(
                None,
                lambda: self.geocoder.geocode(
                    search_query,
                    exactly_one=False,
                    language="tr"
                )
            )
            
            if results:
                locations = []
                center = Location(latitude=latitude, longitude=longitude)
                
                for result in results[:10]:  # Limit to 10 results
                    loc = Location(
                        latitude=result.latitude,
                        longitude=result.longitude,
                        name=result.raw.get("name") or result.address.split(",")[0],
                        address=result.address
                    )
                    
                    # Filter by radius
                    if center.distance_to(loc) <= radius_km:
                        locations.append(loc)
                
                locations.sort(key=lambda l: center.distance_to(l))
                logger.info(f"Found {len(locations)} nearby places", query=query)
                return locations
            
        except Exception as e:
            logger.error("Nearby search failed", error=str(e))
        
        return []
    
    def calculate_distance(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        """
        Calculate distance between two points in kilometers.
        Uses geodesic distance for accuracy.
        """
        return geodesic((lat1, lon1), (lat2, lon2)).kilometers
    
    def estimate_walking_time(
        self,
        distance_km: float,
        pace: float = 5.0
    ) -> int:
        """
        Estimate walking time in minutes.
        
        Args:
            distance_km: Distance in kilometers
            pace: Walking pace in km/h (default 5 km/h)
        
        Returns:
            Estimated time in minutes
        """
        hours = distance_km / pace
        return int(hours * 60)


# Singleton instance
gps_handler = GPSHandler()
