"""
ASTRAEUS - Autonomous Life Orchestrator
Transit Finder Module

This module finds nearby public transit stops (bus, metro, tram)
using OpenStreetMap Overpass API.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import httpx
import asyncio
import structlog

from src.config import settings
from src.location.gps_handler import Location

logger = structlog.get_logger()

# Overpass API endpoint
OVERPASS_API_URL = "https://overpass-api.de/api/interpreter"


@dataclass
class TransitStop:
    """Represents a public transit stop."""
    id: str
    name: str
    latitude: float
    longitude: float
    stop_type: str  # "bus", "metro", "tram", "train"
    lines: List[str] = None
    distance_km: float = 0.0
    walking_minutes: int = 0
    
    @property
    def coords(self) -> tuple:
        return (self.latitude, self.longitude)
    
    def __post_init__(self):
        if self.lines is None:
            self.lines = []


class TransitFinder:
    """
    Finds nearby public transit stops using OpenStreetMap data.
    """
    
    def __init__(self):
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        logger.info("Transit finder initialized")
    
    async def find_nearby_stops(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 500,
        stop_types: Optional[List[str]] = None
    ) -> List[TransitStop]:
        """
        Find public transit stops near a location.
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
            radius_meters: Search radius in meters
            stop_types: Filter by stop types ("bus", "metro", "tram", "train")
        
        Returns:
            List of TransitStop objects sorted by distance
        """
        if stop_types is None:
            stop_types = ["bus", "metro", "tram"]
        
        # Build Overpass query
        queries = []
        for stop_type in stop_types:
            if stop_type == "bus":
                queries.append(f'node["highway"="bus_stop"](around:{radius_meters},{latitude},{longitude});')
                queries.append(f'node["public_transport"="platform"]["bus"="yes"](around:{radius_meters},{latitude},{longitude});')
            elif stop_type == "metro":
                queries.append(f'node["railway"="station"]["station"="subway"](around:{radius_meters},{latitude},{longitude});')
                queries.append(f'node["public_transport"="station"]["subway"="yes"](around:{radius_meters},{latitude},{longitude});')
            elif stop_type == "tram":
                queries.append(f'node["railway"="tram_stop"](around:{radius_meters},{latitude},{longitude});')
            elif stop_type == "train":
                queries.append(f'node["railway"="station"](around:{radius_meters},{latitude},{longitude});')
        
        query = f"""
        [out:json][timeout:10];
        (
            {' '.join(queries)}
        );
        out body;
        """
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    OVERPASS_API_URL,
                    data={"data": query},
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
            
            stops = []
            from geopy.distance import geodesic
            
            for element in data.get("elements", []):
                if element.get("type") != "node":
                    continue
                
                tags = element.get("tags", {})
                stop_lat = element.get("lat")
                stop_lon = element.get("lon")
                
                if not stop_lat or not stop_lon:
                    continue
                
                # Determine stop type
                stop_type = self._determine_stop_type(tags)
                
                # Get stop name
                name = tags.get("name") or tags.get("ref") or f"{stop_type.title()} Durağı"
                
                # Get transit lines if available
                lines = []
                if tags.get("route_ref"):
                    lines = tags.get("route_ref").split(";")
                
                # Calculate distance
                distance_km = geodesic(
                    (latitude, longitude),
                    (stop_lat, stop_lon)
                ).kilometers
                
                # Estimate walking time (5 km/h average walking speed)
                walking_minutes = int((distance_km / 5.0) * 60)
                
                stop = TransitStop(
                    id=str(element.get("id")),
                    name=name,
                    latitude=stop_lat,
                    longitude=stop_lon,
                    stop_type=stop_type,
                    lines=lines,
                    distance_km=round(distance_km, 3),
                    walking_minutes=walking_minutes
                )
                stops.append(stop)
            
            # Sort by distance
            stops.sort(key=lambda s: s.distance_km)
            
            logger.info(
                f"Found {len(stops)} transit stops",
                latitude=latitude,
                longitude=longitude,
                radius=radius_meters
            )
            
            return stops
            
        except httpx.HTTPError as e:
            logger.error("Overpass API request failed", error=str(e))
            return []
        except Exception as e:
            logger.error("Transit search failed", error=str(e))
            return []
    
    def _determine_stop_type(self, tags: Dict[str, Any]) -> str:
        """Determine the type of transit stop from OSM tags."""
        if tags.get("highway") == "bus_stop" or tags.get("bus") == "yes":
            return "bus"
        elif tags.get("station") == "subway" or tags.get("subway") == "yes":
            return "metro"
        elif tags.get("railway") == "tram_stop":
            return "tram"
        elif tags.get("railway") == "station":
            return "train"
        return "bus"  # Default to bus
    
    async def find_nearest_bus_stop(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[TransitStop]:
        """
        Find the nearest bus stop to a location.
        
        Returns:
            Nearest TransitStop or None if not found
        """
        stops = await self.find_nearby_stops(
            latitude,
            longitude,
            radius_meters=1000,  # Search within 1km
            stop_types=["bus"]
        )
        return stops[0] if stops else None
    
    async def find_nearest_metro_station(
        self,
        latitude: float,
        longitude: float
    ) -> Optional[TransitStop]:
        """
        Find the nearest metro station to a location.
        
        Returns:
            Nearest TransitStop or None if not found
        """
        stops = await self.find_nearby_stops(
            latitude,
            longitude,
            radius_meters=2000,  # Search within 2km for metro
            stop_types=["metro"]
        )
        return stops[0] if stops else None
    
    def format_stop_info(self, stop: TransitStop) -> str:
        """Format transit stop information for display."""
        lines_str = ""
        if stop.lines:
            lines_str = f"\n🚌 Hatlar: {', '.join(stop.lines[:5])}"
        
        return f"""📍 {stop.name}
🚶 {stop.distance_km * 1000:.0f} metre ({stop.walking_minutes} dakika yürüme){lines_str}"""


# Singleton instance
transit_finder = TransitFinder()
