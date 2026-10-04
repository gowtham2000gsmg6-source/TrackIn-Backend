from datetime import datetime, timedelta
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
import auth as auth_utils
import models
import schemas
from geofencing import haversine_distance_m
from sms_notifications import send_restricted_area_sms

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


@router.post("/bluetooth-detections", response_model=schemas.BluetoothDetectionResponse)
def bluetooth_detection(
    payload: schemas.BluetoothDetection,
    current_receiver: dict = Depends(auth_utils.get_current_receiver),
    db: Session = Depends(get_db),
):
    receiver = _get_active_receiver(_receiver_id(current_receiver), db)
    now = datetime.utcnow()
    token_hash = hashlib.sha256(payload.beacon_token.encode("ascii")).hexdigest()
    beacon = db.query(models.VisitorBeaconToken).filter(
        models.VisitorBeaconToken.token_hash == token_hash,
        models.VisitorBeaconToken.expires_at > now,
    ).first()
    if not beacon:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Beacon expired or not recognized")
    visitor = db.query(models.Visitor).filter(
        models.Visitor.visitor_id == beacon.visitor_id
    ).first()
    if not visitor or visitor.status == "Exited":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active visitor not found")

    presence = db.query(models.VisitorBluetoothPresence).filter(
        models.VisitorBluetoothPresence.visitor_id == visitor.visitor_id,
        models.VisitorBluetoothPresence.receiver_id == receiver.id,
    ).first()
    entered = presence is None or presence.last_seen_at < now - timedelta(seconds=90)
    if presence is None:
        presence = models.VisitorBluetoothPresence(
            visitor_id=visitor.visitor_id,
            receiver_id=receiver.id,
            rssi=payload.rssi,
            last_seen_at=now,
        )
        db.add(presence)
    else:
        presence.rssi = payload.rssi
        presence.last_seen_at = now

    if entered:
        last_location = db.query(models.Location).filter(
            models.Location.visitor_id == visitor.visitor_id
        ).order_by(models.Location.timestamp.desc()).first()
        latitude = longitude = distance_m = None
        if last_location and last_location.timestamp >= now - timedelta(minutes=2):
            latitude, longitude = last_location.latitude, last_location.longitude
            distance_m = round(haversine_distance_m(
                latitude, longitude, receiver.latitude, receiver.longitude
            ), 2)
        db.add(models.VisitorLocationLog(
            visitor_id=visitor.visitor_id,
            receiver_id=receiver.id,
            timestamp=now,
            latitude=latitude,
            longitude=longitude,
            distance_m=distance_m,
            detected_via="Bluetooth",
        ))
    db.commit()

    if entered and receiver.is_restricted and visitor.restricted_sms_consent:
        send_restricted_area_sms(visitor, receiver.name)

    return schemas.BluetoothDetectionResponse(
        visitor_id=visitor.visitor_id,
        receiver_id=receiver.id,
        receiver_name=receiver.name,
        rssi=payload.rssi,
        last_seen_at=now,
        recorded_entry=entered,
    )
