from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import get_db
import models
import schemas
import auth as auth_utils

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/dashboard", response_model=schemas.DashboardStats)
def dashboard(db: Session = Depends(get_db), current_admin: dict = Depends(auth_utils.get_current_admin)):
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    total_visitors = db.query(models.Visitor).filter(models.Visitor.entry_time >= today_start).count()
    visitors_inside = db.query(models.Visitor).filter(models.Visitor.status == "Inside").count()
    visitors_exited = db.query(models.Visitor).filter(
        models.Visitor.status == "Exited", models.Visitor.exit_time >= today_start
    ).count()

    live = db.query(models.Visitor).filter(models.Visitor.status.in_(["Inside", "Pending Entry"])).all()
    live_visitors = []
    for v in live:
        last_loc = max(v.locations, key=lambda l: l.timestamp) if v.locations else None
        live_visitors.append(schemas.LiveVisitorResponse(
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
        ))

    return schemas.DashboardStats(
        total_visitors=total_visitors,
        visitors_inside=visitors_inside,
        visitors_exited=visitors_exited,
        live_visitors=live_visitors,
    )


@router.get("/analytics", response_model=schemas.AnalyticsResponse)
def analytics(db: Session = Depends(get_db), current_admin: dict = Depends(auth_utils.get_current_admin)):
    total_all_time = db.query(models.Visitor).count()

    dept_rows = db.query(models.Visitor.department, func.count(models.Visitor.visitor_id)).group_by(
        models.Visitor.department
    ).all()
    visits_by_department = [schemas.DepartmentStats(department=d or "Unknown", count=c) for d, c in dept_rows]

    hour_rows = db.query(
        func.strftime("%H:00", models.Visitor.entry_time), func.count(models.Visitor.visitor_id)
    ).group_by(func.strftime("%H:00", models.Visitor.entry_time)).all()
    visits_by_hour = [schemas.HourlyVisitStats(hour=h, count=c) for h, c in hour_rows]

    durations = []
    for v in db.query(models.Visitor).filter(models.Visitor.exit_time.isnot(None)).all():
        durations.append((v.exit_time - v.entry_time).total_seconds() / 60.0)
    average_duration_minutes = round(sum(durations) / len(durations), 1) if durations else 0.0

    return schemas.AnalyticsResponse(
        total_all_time=total_all_time,
        visits_by_department=visits_by_department,
        visits_by_hour=visits_by_hour,
        average_duration_minutes=average_duration_minutes,
    )


@router.get("/location-receivers", response_model=list[schemas.LocationReceiverResponse])
def list_location_receivers(
    db: Session = Depends(get_db),
    current_admin: dict = Depends(auth_utils.get_current_admin),
):
    return db.query(models.LocationReceiver).order_by(models.LocationReceiver.name).all()


@router.post(
    "/location-receivers",
    response_model=schemas.LocationReceiverResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_location_receiver(
    payload: schemas.LocationReceiverCreate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(auth_utils.get_current_admin),
):
    if not payload.name.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Receiver name is required")
    receiver = models.LocationReceiver(
        name=payload.name.strip(),
        latitude=payload.latitude,
        longitude=payload.longitude,
        radius_m=payload.radius_m,
        is_restricted=payload.is_restricted,
        pin_hash=auth_utils.hash_password(payload.pin),
    )
    db.add(receiver)
    db.commit()
    db.refresh(receiver)
    return receiver


@router.patch("/location-receivers/{receiver_id}", response_model=schemas.LocationReceiverResponse)
def update_location_receiver(
    receiver_id: int,
    payload: schemas.LocationReceiverUpdate,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(auth_utils.get_current_admin),
):
    receiver = db.query(models.LocationReceiver).filter(models.LocationReceiver.id == receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Location receiver not found")

    updates = payload.model_dump(exclude_unset=True)
    pin = updates.pop("pin", None)
    if any(value is None for value in updates.values()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Receiver update values cannot be null",
        )
    if "name" in updates and not updates["name"].strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Receiver name is required")
    for field, value in updates.items():
        setattr(receiver, field, value.strip() if field == "name" else value)
    if pin is not None:
        receiver.pin_hash = auth_utils.hash_password(pin)
    if updates.get("status") == "inactive":
        db.query(models.VisitorGeofenceState).filter(
            models.VisitorGeofenceState.receiver_id == receiver.id
        ).update(
            {
                models.VisitorGeofenceState.is_inside: False,
                models.VisitorGeofenceState.updated_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
    db.commit()
    db.refresh(receiver)
    return receiver


@router.get("/visitor-location-logs", response_model=list[schemas.VisitorLocationLogResponse])
def visitor_location_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: dict = Depends(auth_utils.get_current_admin),
):
    limit = min(max(limit, 1), 500)
    rows = (
        db.query(models.VisitorLocationLog, models.LocationReceiver.name)
        .join(models.LocationReceiver, models.VisitorLocationLog.receiver_id == models.LocationReceiver.id)
        .order_by(models.VisitorLocationLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return [
        schemas.VisitorLocationLogResponse(
            id=log.id,
            visitor_id=log.visitor_id,
            receiver_id=log.receiver_id,
            receiver_name=receiver_name,
            timestamp=log.timestamp,
            latitude=log.latitude,
            longitude=log.longitude,
            distance_m=log.distance_m,
            detected_via=log.detected_via,
        )
        for log, receiver_name in rows
    ]
