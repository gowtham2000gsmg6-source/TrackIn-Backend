from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Literal
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
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    accuracy: float = Field(..., ge=0)
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

class NearbyBluetoothDevice(BaseModel):
    receiver_id: int
    receiver_name: str
    rssi: int
    last_seen_at: datetime


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
    nearby_bluetooth: List[NearbyBluetoothDevice] = Field(default_factory=list)

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


class ReceiverLogin(BaseModel):
    receiver_id: int = Field(..., ge=1)
    pin: str = Field(..., min_length=6, max_length=12, pattern=r"^\d+$")


class ReceiverSessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str = "receiver"
    receiver_id: int
    name: str
    latitude: float
    longitude: float
    radius_m: float
    is_restricted: bool
    status: str


class LocationReceiverCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_m: float = Field(..., gt=0, le=10000)
    is_restricted: bool = False
    pin: str = Field(..., min_length=6, max_length=12, pattern=r"^\d+$")


class LocationReceiverUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=120)
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    radius_m: Optional[float] = Field(None, gt=0, le=10000)
    is_restricted: Optional[bool] = None
    status: Optional[Literal["active", "inactive"]] = None
    pin: Optional[str] = Field(None, min_length=6, max_length=12, pattern=r"^\d+$")


class LocationReceiverResponse(BaseModel):
    id: int
    name: str
    latitude: float
    longitude: float
    radius_m: float
    is_restricted: bool
    status: str
    last_seen_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class VisitorLocationLogResponse(BaseModel):
    id: int
    visitor_id: str
    receiver_id: int
    receiver_name: str
    timestamp: datetime
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    distance_m: Optional[float] = None
    detected_via: Literal["GPS", "Bluetooth"]


class BluetoothDetection(BaseModel):
    beacon_token: str = Field(..., min_length=16, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")
    rssi: int = Field(..., ge=-127, le=20)


class BeaconTokenResponse(BaseModel):
    beacon_token: str
    expires_at: datetime


class BluetoothDetectionResponse(BaseModel):
    visitor_id: str
    receiver_id: int
    receiver_name: str
    rssi: int
    last_seen_at: datetime
    recorded_entry: bool
