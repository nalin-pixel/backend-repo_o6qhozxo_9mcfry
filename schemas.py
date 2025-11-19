"""
Database Schemas for Racing UI (FiveM-style)

Each Pydantic model corresponds to a MongoDB collection. The collection name is the lowercase
class name (e.g., Race -> "race").
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class Vehicle(BaseModel):
    """
    Vehicles that can be selected for a race
    Collection: "vehicle"
    """
    name: str = Field(..., description="Display name, e.g., Zentorno")
    code: str = Field(..., description="Spawn code / identifier")
    class_name: Optional[str] = Field(None, description="Vehicle class/category")
    is_enabled: bool = Field(True, description="Whether the vehicle is selectable")


class Map(BaseModel):
    """
    Race maps/tracks available to run
    Collection: "map"
    """
    name: str = Field(..., description="Map name")
    code: str = Field(..., description="Unique code/slug for the map")
    author: Optional[str] = Field(None, description="Map author")
    lap_length_m: Optional[int] = Field(None, ge=0, description="Approx lap length in meters")
    checkpoints: Optional[List[dict]] = Field(None, description="List of checkpoints with coords")
    is_enabled: bool = Field(True)


class Race(BaseModel):
    """
    A race session with chosen map, laps and allowed vehicles
    Collection: "race"
    """
    map_code: str = Field(...)
    laps: int = Field(..., ge=1, le=100)
    allowed_vehicle_codes: List[str] = Field(default_factory=list)
    created_by: Optional[str] = Field(None)
    status: str = Field("pending", description="pending|active|finished|cancelled")
    starts_at: Optional[datetime] = None


class Entry(BaseModel):
    """
    Per-player race entry for results/leaderboard
    Collection: "entry"
    """
    race_id: str = Field(...)
    player_name: str = Field(...)
    vehicle_code: str = Field(...)
    total_time_ms: Optional[int] = Field(None, ge=0)
    best_lap_ms: Optional[int] = Field(None, ge=0)
    laps_completed: int = Field(0, ge=0)
    position: Optional[int] = Field(None, ge=1)
