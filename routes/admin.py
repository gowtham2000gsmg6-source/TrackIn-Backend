from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
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
