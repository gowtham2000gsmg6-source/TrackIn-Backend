from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# Auth schemas
class AdminLogin(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str

# Visitor Registration schemas
class VisitorRegister(BaseModel):
    full_name: str = Field(..., min_length=1)
    phone_number: str = Field(..., min_length=10)
    email: Optional[EmailStr] = None
    department: str
    person_to_meet: str
    purpose: str
    device_info: Optional[str] = None
    browser_info: Optional[str] = None

class VisitorRegisterResponse(BaseModel):
    visitor_id: str
    full_name: str
    access_token: str
    token_type: str = "bearer"

# Location Update schemas
class LocationUpdate(BaseModel):
    latitude: float
    longitude: float
    accuracy: float
    speed: Optional[float] = None
    heading: Optional[float] = None

class LocationResponse(BaseModel):
    visitor_id: str
    latitude: float
    longitude: float
    accuracy: float
    speed: Optional[float] = None
    heading: Optional[float] = None
    timestamp: datetime
    source: str

    class Config:
        from_attributes = True

# Future BLE Location Schema Placeholder
class BLELocationUpdate(BaseModel):
    beacon_uuid: str
    major: int
    minor: int
    rssi: float
    tx_power: Optional[int] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class VisitorStatusUpdate(BaseModel):
    gps_enabled: bool
    bluetooth_enabled: bool

# Visitor details schemas
class VisitorResponse(BaseModel):
    visitor_id: str
    full_name: str
    phone_number: str
    email: Optional[str] = None
    department: str
    person_to_meet: str
    purpose: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    status: str
    device_info: Optional[str] = None
    browser_info: Optional[str] = None
    gps_enabled: bool
    bluetooth_enabled: bool
    locations: Optional[List[LocationResponse]] = []

    class Config:
        from_attributes = True

class LiveVisitorResponse(BaseModel):
    visitor_id: str
    full_name: str
    phone_number: str
    department: str
    purpose: str
    entry_time: datetime
    status: str
    last_latitude: Optional[float] = None
    last_longitude: Optional[float] = None
    last_updated: Optional[datetime] = None
    gps_enabled: bool
    bluetooth_enabled: bool

# Admin Dashboard schemas
class DashboardStats(BaseModel):
    total_visitors: int
    visitors_inside: int
    visitors_exited: int
    live_visitors: List[LiveVisitorResponse]

# Admin Analytics schemas
class DepartmentStats(BaseModel):
    department: str
    count: int

class HourlyVisitStats(BaseModel):
    hour: str
    count: int

class AnalyticsResponse(BaseModel):
    total_all_time: int
    visits_by_department: List[DepartmentStats]
    visits_by_hour: List[HourlyVisitStats]
    average_duration_minutes: float
