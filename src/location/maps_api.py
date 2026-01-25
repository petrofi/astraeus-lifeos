"""
ASTRAEUS - Autonomous Life Orchestrator
Maps API Module

This module provides routing and travel time calculations
using either Google Maps or OpenStreetMap/OSRM.
"""

from dataclasses import dataclass
from typing import Optional, List, Tuple, Literal
from datetime import datetime, timedelta
import httpx
import asyncio
import structlog

from src.config import settings

logger = structlog.get_logger()

# OSRM endpoints (free routing)
OSRM_DRIVING_URL = "https://router.project-osrm.org/route/v1/driving"
OSRM_WALKING_URL = "https://router.project-osrm.org/route/v1/foot"
OSRM_CYCLING_URL = "https://router.project-osrm.org/route/v1/bike"


@dataclass
class RouteStep:
    """A single step in a route."""
    instruction: str
    distance_meters: float
    duration_seconds: float
    maneuver_type: str = ""


@dataclass
class Route:
    """Represents a calculated route between two points."""
    origin: Tuple[float, float]
    destination: Tuple[float, float]
    distance_km: float
    duration_minutes: int
    transport_mode: str
    steps: List[RouteStep] = None
    polyline: str = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []


class MapsAPI:
    """
    Provides routing and navigation services.
    Supports both Google Maps and free OSRM.
    """
    
    def __init__(self, use_google: bool = False, google_api_key: str = None):
        self.use_google = use_google and google_api_key
        self.google_api_key = google_api_key
        self.cache = {}
        
        if self.use_google:
            logger.info("Maps API initialized with Google Maps")
        else:
            logger.info("Maps API initialized with OSRM (free)")
    
    async def get_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: Literal["driving", "walking", "cycling", "transit"] = "driving"
    ) -> Optional[Route]:
        """
        Calculate a route between two points.
        
        Args:
            origin_lat: Starting latitude
            origin_lon: Starting longitude
            dest_lat: Destination latitude
            dest_lon: Destination longitude
            mode: Transport mode
        
        Returns:
            Route object with distance and duration
        """
        if self.use_google:
            return await self._get_google_route(
                origin_lat, origin_lon, dest_lat, dest_lon, mode
            )
        else:
            return await self._get_osrm_route(
                origin_lat, origin_lon, dest_lat, dest_lon, mode
            )
    
    async def _get_osrm_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: str
    ) -> Optional[Route]:
        """Get route using free OSRM service."""
        
        # Select appropriate OSRM endpoint
        if mode == "walking":
            base_url = OSRM_WALKING_URL
        elif mode == "cycling":
            base_url = OSRM_CYCLING_URL
        else:
            base_url = OSRM_DRIVING_URL
        
        # OSRM uses lon,lat order
        url = f"{base_url}/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        params = {
            "overview": "simplified",
            "steps": "true",
            "geometries": "polyline"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            if data.get("code") != "Ok":
                logger.warning("OSRM routing failed", code=data.get("code"))
                return None
            
            route_data = data.get("routes", [{}])[0]
            
            # Parse steps
            steps = []
            for leg in route_data.get("legs", []):
                for step in leg.get("steps", []):
                    steps.append(RouteStep(
                        instruction=step.get("name", ""),
                        distance_meters=step.get("distance", 0),
                        duration_seconds=step.get("duration", 0),
                        maneuver_type=step.get("maneuver", {}).get("type", "")
                    ))
            
            route = Route(
                origin=(origin_lat, origin_lon),
                destination=(dest_lat, dest_lon),
                distance_km=round(route_data.get("distance", 0) / 1000, 2),
                duration_minutes=int(route_data.get("duration", 0) / 60),
                transport_mode=mode,
                steps=steps,
                polyline=route_data.get("geometry")
            )
            
            logger.info(
                "Route calculated",
                distance_km=route.distance_km,
                duration_min=route.duration_minutes,
                mode=mode
            )
            
            return route
            
        except httpx.HTTPError as e:
            logger.error("OSRM request failed", error=str(e))
            return None
        except Exception as e:
            logger.error("Route calculation failed", error=str(e))
            return None
    
    async def _get_google_route(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: str
    ) -> Optional[Route]:
        """Get route using Google Maps Directions API."""
        
        if mode == "cycling":
            mode = "bicycling"
        
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            "origin": f"{origin_lat},{origin_lon}",
            "destination": f"{dest_lat},{dest_lon}",
            "mode": mode,
            "key": self.google_api_key,
            "language": "tr"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") != "OK":
                logger.warning("Google Maps API error", status=data.get("status"))
                return None
            
            route_data = data.get("routes", [{}])[0]
            leg = route_data.get("legs", [{}])[0]
            
            # Parse steps
            steps = []
            for step in leg.get("steps", []):
                steps.append(RouteStep(
                    instruction=step.get("html_instructions", ""),
                    distance_meters=step.get("distance", {}).get("value", 0),
                    duration_seconds=step.get("duration", {}).get("value", 0),
                    maneuver_type=step.get("maneuver", "")
                ))
            
            route = Route(
                origin=(origin_lat, origin_lon),
                destination=(dest_lat, dest_lon),
                distance_km=round(leg.get("distance", {}).get("value", 0) / 1000, 2),
                duration_minutes=int(leg.get("duration", {}).get("value", 0) / 60),
                transport_mode=mode,
                steps=steps,
                polyline=route_data.get("overview_polyline", {}).get("points")
            )
            
            logger.info(
                "Google route calculated",
                distance_km=route.distance_km,
                duration_min=route.duration_minutes,
                mode=mode
            )
            
            return route
            
        except httpx.HTTPError as e:
            logger.error("Google Maps request failed", error=str(e))
            return None
        except Exception as e:
            logger.error("Google route calculation failed", error=str(e))
            return None
    
    async def get_travel_time(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: str = "driving"
    ) -> Optional[int]:
        """
        Get travel time in minutes between two points.
        
        Returns:
            Travel time in minutes, or None if calculation fails
        """
        route = await self.get_route(
            origin_lat, origin_lon,
            dest_lat, dest_lon,
            mode
        )
        return route.duration_minutes if route else None
    
    async def get_distance(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float
    ) -> Optional[float]:
        """
        Get distance in kilometers between two points.
        Uses driving route for accuracy.
        
        Returns:
            Distance in kilometers, or None if calculation fails
        """
        route = await self.get_route(
            origin_lat, origin_lon,
            dest_lat, dest_lon,
            "driving"
        )
        return route.distance_km if route else None
    
    def format_route_summary(self, route: Route) -> str:
        """Format route information for display."""
        mode_emoji = {
            "driving": "🚗",
            "walking": "🚶",
            "cycling": "🚴",
            "transit": "🚌"
        }.get(route.transport_mode, "🗺️")
        
        return f"""{mode_emoji} {route.transport_mode.capitalize()}
📏 Mesafe: {route.distance_km} km
⏱️ Süre: {route.duration_minutes} dakika"""


# Create singleton with settings
def get_maps_api() -> MapsAPI:
    """Factory function to get Maps API instance based on settings."""
    if settings.use_openstreetmap:
        return MapsAPI(use_google=False)
    else:
        return MapsAPI(
            use_google=True,
            google_api_key=settings.google_maps_api_key
        )


maps_api = get_maps_api()
