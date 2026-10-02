from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import auth as auth_utils
import models
import schemas
from geofencing import haversine_distance_m

router = APIRouter(prefix="/receivers", tags=["Location receivers"])


def _get_active_receiver(receiver_id: int, db: Session) -> models.LocationReceiver:
    receiver = db.query(models.LocationReceiver).filter(
        models.LocationReceiver.id == receiver_id
    ).first()
    if not receiver or receiver.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Location receiver is inactive")
    return receiver


def _receiver_id(payload: dict) -> int:
    try:
        return int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid receiver session")


@router.post("/login", response_model=schemas.ReceiverSessionResponse)
def receiver_login(payload: schemas.ReceiverLogin, db: Session = Depends(get_db)):
    receiver = db.query(models.LocationReceiver).filter(
        models.LocationReceiver.id == payload.receiver_id
    ).first()
    if not receiver or receiver.status != "active" or not auth_utils.verify_password(payload.pin, receiver.pin_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid receiver ID or PIN")

    token = auth_utils.create_access_token(
        data={"sub": str(receiver.id), "role": "receiver"},
        expires_delta=timedelta(hours=12),
    )
    return schemas.ReceiverSessionResponse(
        access_token=token,
        receiver_id=receiver.id,
        name=receiver.name,
        latitude=receiver.latitude,
        longitude=receiver.longitude,
        radius_m=receiver.radius_m,
        is_restricted=receiver.is_restricted,
        status=receiver.status,
    )


@router.get("/me", response_model=schemas.LocationReceiverResponse)
def receiver_me(
    current_receiver: dict = Depends(auth_utils.get_current_receiver),
    db: Session = Depends(get_db),
):
    return _get_active_receiver(_receiver_id(current_receiver), db)


@router.post("/heartbeat", response_model=schemas.LocationReceiverResponse)
def receiver_heartbeat(
    current_receiver: dict = Depends(auth_utils.get_current_receiver),
    db: Session = Depends(get_db),
):
    receiver = _get_active_receiver(_receiver_id(current_receiver), db)
    receiver.last_seen_at = datetime.utcnow()
    db.commit()
    db.refresh(receiver)
    return receiver


@router.post("/bluetooth-detections", response_model=schemas.VisitorLocationLogResponse)
def bluetooth_detection(
    payload: schemas.BluetoothDetection,
    current_receiver: dict = Depends(auth_utils.get_current_receiver),
    db: Session = Depends(get_db),
):
    receiver = _get_active_receiver(_receiver_id(current_receiver), db)
    visitor = db.query(models.Visitor).filter(
        models.Visitor.visitor_id == payload.visitor_id
    ).first()
    if not visitor or visitor.status == "Exited":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active visitor not found")

    now = datetime.utcnow()
    previous = db.query(models.VisitorLocationLog).filter(
        models.VisitorLocationLog.visitor_id == visitor.visitor_id,
        models.VisitorLocationLog.receiver_id == receiver.id,
        models.VisitorLocationLog.detected_via == "Bluetooth",
        models.VisitorLocationLog.timestamp >= now - timedelta(seconds=60),
    ).order_by(models.VisitorLocationLog.timestamp.desc()).first()
    if previous:
        log = previous
    else:
        last_location = db.query(models.Location).filter(
            models.Location.visitor_id == visitor.visitor_id
        ).order_by(models.Location.timestamp.desc()).first()
        distance_m = None
        latitude = longitude = None
        if last_location and last_location.timestamp >= now - timedelta(minutes=2):
            latitude, longitude = last_location.latitude, last_location.longitude
            distance_m = round(haversine_distance_m(
                latitude, longitude, receiver.latitude, receiver.longitude
            ), 2)
        log = models.VisitorLocationLog(
            visitor_id=visitor.visitor_id,
            receiver_id=receiver.id,
            timestamp=now,
            latitude=latitude,
            longitude=longitude,
            distance_m=distance_m,
            detected_via="Bluetooth",
        )
        db.add(log)
        state = db.query(models.VisitorGeofenceState).filter(
            models.VisitorGeofenceState.visitor_id == visitor.visitor_id,
            models.VisitorGeofenceState.receiver_id == receiver.id,
        ).first()
        if state:
            state.is_inside = True
            state.updated_at = now
        else:
            db.add(models.VisitorGeofenceState(
                visitor_id=visitor.visitor_id,
                receiver_id=receiver.id,
                is_inside=True,
                updated_at=now,
            ))
        db.commit()
        db.refresh(log)

    return schemas.VisitorLocationLogResponse(
        id=log.id,
        visitor_id=log.visitor_id,
        receiver_id=log.receiver_id,
        receiver_name=receiver.name,
        timestamp=log.timestamp,
        latitude=log.latitude,
        longitude=log.longitude,
        distance_m=log.distance_m,
        detected_via=log.detected_via,
    )
