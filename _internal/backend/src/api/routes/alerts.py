from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ...database.database import get_db
from ...database.crud import get_alerts, acknowledge_alert
from ...database.models import User
from ...api.dependencies import get_current_active_user

router = APIRouter()


class AlertResponse(BaseModel):
    id: int
    zone: str
    sensor_type: str
    reason: str
    severity: str
    value: Optional[float]
    threshold: Optional[float]
    recommendation: Optional[str]
    acknowledged: bool
    timestamp: datetime


@router.get("/alerts", response_model=List[AlertResponse])
def get_alerts_endpoint(
        acknowledged: Optional[bool] = None,
        hours: int = 24,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    alerts = get_alerts(db, current_user.id, acknowledged, hours)
    return [AlertResponse(**alert.__dict__) for alert in alerts]


@router.post("/alerts/{alert_id}/acknowledge")
def acknowledge_alert_endpoint(
        alert_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    alert = acknowledge_alert(db, alert_id, current_user.id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {
        "success": True,
        "message": "Alert acknowledged",
        "alert_id": alert_id
    }


@router.get("/data/alerts")
def get_alerts_data(
        acknowledged: bool = False,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_active_user)
):
    alerts = get_alerts(db, current_user.id, acknowledged, hours=24)

    return [
        {
            "id": alert.id,
            "reason": alert.reason,
            "severity": alert.severity,
            "value": alert.value,
            "recommendation": alert.recommendation,
            "acknowledged": alert.acknowledged,
            "timestamp": alert.timestamp.isoformat(),
            "critical": alert.severity == "critical"
        }
        for alert in alerts
    ]