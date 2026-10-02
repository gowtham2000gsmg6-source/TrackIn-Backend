from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Visitor(Base):
    __tablename__ = "visitors"

    visitor_id = Column(String, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    email = Column(String, nullable=True)
    department = Column(String, nullable=False)
    person_to_meet = Column(String, nullable=False)
    purpose = Column(String, nullable=False)
    entry_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    status = Column(String, default="Pending Entry", nullable=False)  # "Pending Entry", "Inside", "Pending Exit", "Exited"
    device_info = Column(String, nullable=True)
    browser_info = Column(String, nullable=True)
    
    # Security alerts flags
    gps_enabled = Column(Boolean, default=True, nullable=False)
    bluetooth_enabled = Column(Boolean, default=True, nullable=False)

    # Relationships
    locations = relationship("Location", back_populates="visitor", cascade="all, delete-orphan")
    bluetooth_device = relationship(
        "VisitorBluetoothDevice",
        back_populates="visitor",
        cascade="all, delete-orphan",
        uselist=False,
    )

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    visitor_id = Column(String, ForeignKey("visitors.visitor_id", ondelete="CASCADE"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    accuracy = Column(Float, nullable=False)
    speed = Column(Float, nullable=True)
    heading = Column(Float, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String, default="GPS", nullable=False)  # "GPS" or "BLE"

    # Relationships
    visitor = relationship("Visitor", back_populates="locations")


class VisitorBluetoothDevice(Base):
    __tablename__ = "visitor_bluetooth_devices"

    visitor_id = Column(
        String,
        ForeignKey("visitors.visitor_id", ondelete="CASCADE"),
        primary_key=True,
    )
    device_name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    visitor = relationship("Visitor", back_populates="bluetooth_device")


class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class LocationReceiver(Base):
    __tablename__ = "location_receivers"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    radius_m = Column(Float, nullable=False)
    is_restricted = Column(Boolean, default=False, nullable=False)
    status = Column(String, default="active", nullable=False)
    pin_hash = Column(String, nullable=False)
    last_seen_at = Column(DateTime, nullable=True)


class VisitorLocationLog(Base):
    __tablename__ = "visitor_location_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    visitor_id = Column(String, ForeignKey("visitors.visitor_id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_id = Column(Integer, ForeignKey("location_receivers.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    distance_m = Column(Float, nullable=True)
    detected_via = Column(String, nullable=False)


class VisitorGeofenceState(Base):
    __tablename__ = "visitor_geofence_states"
    __table_args__ = (UniqueConstraint("visitor_id", "receiver_id", name="uq_visitor_receiver_geofence"),)

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    visitor_id = Column(String, ForeignKey("visitors.visitor_id", ondelete="CASCADE"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("location_receivers.id", ondelete="CASCADE"), nullable=False)
    is_inside = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
