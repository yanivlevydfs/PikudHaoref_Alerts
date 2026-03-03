from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AlertData(BaseModel):
    id: str = Field(..., description="Unique alert identifier")
    cat: str = Field(..., description="Category ID")
    title: str = Field(..., description="Alert title (Hebrew)")
    data: List[str] = Field(..., description="List of affected city/area names")
    desc: str = Field(..., description="Safety instructions (Hebrew)")

class AlertsResponse(BaseModel):
    message: str = Field(..., description="Summary of the request result")
    data: Optional[AlertData] = Field(None, description="Active alert data, if any")
    is_online: bool = Field(..., description="Backend system connection status")

class HistoryItem(BaseModel):
    alert_id: str
    title: str
    description: str
    locations: List[str]
    timestamp: str

class HistoryResponse(BaseModel):
    message: str
    data: List[HistoryItem]

class StatisticsResponse(BaseModel):
    message: str
    data: List[Dict[str, Any]]

class GeocodeRequest(BaseModel):
    cities: List[str] = Field(..., description="List of city names to resolve coordinates for.")

class GeocodeResponse(BaseModel):
    message: str
    data: Dict[str, Any] = Field(..., description="Dictionary mapping city name to GeoJSON data.")
