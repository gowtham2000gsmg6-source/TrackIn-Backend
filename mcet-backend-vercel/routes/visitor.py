import uuid
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models
import schemas
import auth as auth_utils

router = APIRouter(prefix="/visitors", tags=["Visitors"])


def _next_visitor_id(db: Session) -> str:
    last = db.query(models.Visitor).order_by(models.Visitor.visitor_id.desc()).first()
    if last and last.visitor_id.startswith("MCET-"):
        try:
            n = int(last.visitor_id.split("-")[1]) + 1
        except (IndexError, ValueError):
            n = db.query(models.Visitor).count() + 1
    else:
        n = db.query(models.Visitor).count() + 1
    return f"MCET-{n:04d}"


def _to_live_response(v: models.Visitor) -> schemas.LiveVisitorResponse:
    last_loc = max(v.locations, key=lambda l: l.timestamp) if v.locations else None
    return schemas.LiveVisitorResponse(
        visitor_id=v.visitor_id,
        full_name=v.full_name,
        phone_number=v.phone_number,
        department=v.department,
        purpose=v.purpose,
        entry_time=v.entry_time,
        status=v.status,
        last_latitude=last_loc.latitude if last_loc else None,
        last_longitude=last_loc.longitude if last_loc else None,
        last_updated=last_loc.timestamp if last_loc else None,
        gps_enabled=v.gps_enabled,
        bluetooth_enabled=v.bluetooth_enabled,
    )


# ---------- Gate staff: check-in / check-out (admin-authenticated) ----------

@router.post("/check-in", response_model=schemas.VisitorResponse, status_code=status.HTTP_201_CREATED)
def check_in(payload: schemas.VisitorRegister, db: Session = Depends(get_db),
             current_admin: dict = Depends(auth_utils.get_current_admin)):
    """Gate staff logs a walk-in visitor. Sets status to 'Inside' immediately."""
    visitor = models.Visitor(
        visitor_id=_next_visitor_id(db),
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        email=payload.email,
        department=payload.department,
        person_to_meet=payload.person_to_meet,
        purpose=payload.purpose,
        entry_time=datetime.utcnow(),
        status="Inside",
        device_info=payload.device_info,
        browser_info=payload.browser_info,
    )
    db.add(visitor)
    db.commit()
    db.refresh(visitor)
    return visitor


@router.post("/admit/{visitor_id}", response_model=schemas.VisitorResponse)
def admit(visitor_id: str, db: Session = Depends(get_db),
          current_admin: dict = Depends(auth_utils.get_current_admin)):
    """Gate staff approves a self-registered visitor (status 'Pending Entry')
    and admits them onto campus, setting status to 'Inside'."""
    visitor = db.query(models.Visitor).filter(models.Visitor.visitor_id == visitor_id).first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    if visitor.status != "Pending Entry":
        raise HTTPException(status_code=400, detail=f"Visitor is '{visitor.status}', not awaiting entry")

    visitor.status = "Inside"
    visitor.entry_time = datetime.utcnow()
    db.commit()
    db.refresh(visitor)
    return visitor


@router.post("/check-out/{visitor_id}", response_model=schemas.VisitorResponse)
def check_out(visitor_id: str, db: Session = Depends(get_db),
              current_admin: dict = Depends(auth_utils.get_current_admin)):
    visitor = db.query(models.Visitor).filter(models.Visitor.visitor_id == visitor_id).first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    if visitor.status == "Exited":
        raise HTTPException(status_code=400, detail="Visitor already checked out")

    visitor.exit_time = datetime.utcnow()
    visitor.status = "Exited"
    db.commit()
    db.refresh(visitor)
    return visitor


@router.get("/active", response_model=List[schemas.VisitorResponse])
def list_active(db: Session = Depends(get_db),
                 current_admin: dict = Depends(auth_utils.get_current_admin)):
    return db.query(models.Visitor).filter(models.Visitor.status == "Inside").order_by(
        models.Visitor.entry_time.desc()
    ).all()


@router.get("/history", response_model=List[schemas.VisitorResponse])
def history(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(auth_utils.get_current_admin),
    start_date: Optional[datetime] = Query(None, description="ISO date, filters entry_time >="),
    end_date: Optional[datetime] = Query(None, description="ISO date, filters entry_time <="),
    department: Optional[str] = None,
    search: Optional[str] = Query(None, description="matches name or phone"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    q = db.query(models.Visitor)
    if start_date:
        q = q.filter(models.Visitor.entry_time >= start_date)
    if end_date:
        q = q.filter(models.Visitor.entry_time <= end_date)
    if department:
        q = q.filter(models.Visitor.department == department)
    if search:
        like = f"%{search}%"
        q = q.filter((models.Visitor.full_name.ilike(like)) | (models.Visitor.phone_number.ilike(like)))

    q = q.order_by(models.Visitor.entry_time.desc())
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return items


@router.get("/{visitor_id}", response_model=schemas.VisitorResponse)
def get_visitor(visitor_id: str, db: Session = Depends(get_db),
                 current_admin: dict = Depends(auth_utils.get_current_admin)):
    visitor = db.query(models.Visitor).filter(models.Visitor.visitor_id == visitor_id).first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")
    return visitor


# ---------- Visitor self-service (kiosk/QR registration + live GPS/BLE) ----------

@router.post("/register", response_model=schemas.VisitorRegisterResponse, status_code=status.HTTP_201_CREATED)
def self_register(payload: schemas.VisitorRegister, db: Session = Depends(get_db)):
    """Visitor scans a QR at the gate and registers themselves; returns a
    short-lived visitor token used only to push GPS/BLE location updates."""
    visitor = models.Visitor(
        visitor_id=_next_visitor_id(db),
        full_name=payload.full_name,
        phone_number=payload.phone_number,
        email=payload.email,
        department=payload.department,
        person_to_meet=payload.person_to_meet,
        purpose=payload.purpose,
        entry_time=datetime.utcnow(),
        status="Pending Entry",
        device_info=payload.device_info,
        browser_info=payload.browser_info,
    )
    db.add(visitor)
    db.commit()
    db.refresh(visitor)

    token = auth_utils.create_access_token(
        data={"sub": visitor.visitor_id, "role": "visitor"},
        expires_delta=timedelta(hours=12),
    )
    return schemas.VisitorRegisterResponse(
        visitor_id=visitor.visitor_id, full_name=visitor.full_name, access_token=token
    )


@router.post("/location", response_model=schemas.LocationResponse, status_code=status.HTTP_201_CREATED)
def push_location(payload: schemas.LocationUpdate, db: Session = Depends(get_db),
                   current_visitor: dict = Depends(auth_utils.get_current_visitor)):
    visitor_id = current_visitor.get("sub")
    visitor = db.query(models.Visitor).filter(models.Visitor.visitor_id == visitor_id).first()
    if not visitor:
        raise HTTPException(status_code=404, detail="Visitor not found")

    loc = models.Location(
        visitor_id=visitor_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
        accuracy=payload.accuracy,
        speed=payload.speed,
        heading=payload.heading,
        timestamp=datetime.utcnow(),
        source="GPS",
    )
    db.add(loc)
    db.commit()
    db.refresh(loc)
    return loc


@router.get("/live/all", response_model=List[schemas.LiveVisitorResponse])
def live_all(db: Session = Depends(get_db), current_admin: dict = Depends(auth_utils.get_current_admin)):
    visitors = db.query(models.Visitor).filter(models.Visitor.status.in_(["Inside", "Pending Entry"])).all()
    return [_to_live_response(v) for v in visitors]
