from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
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

class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
