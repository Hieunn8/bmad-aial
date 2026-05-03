"""In-memory anomaly detection and alert history service for Story 7.2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from fastapi import HTTPException

from aial_shared.auth.keycloak import JWTClaims


class AlertSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnomalyAlertStatus(StrEnum):
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    DISMISSED = "dismissed"


@dataclass(frozen=True)
class TimeSeriesPoint:
    timestamp: str
    actual: float
    expected_min: float
    expected_max: float
    is_anomaly: bool = False


@dataclass
class AnomalyAlert:
    alert_id: str
    metric_name: str
    domain: str
    department_scope: str
    region: str
    anomaly_timestamp: str
    deviation_percent: float
    severity: AlertSeverity
    isolation_forest_score: float
    false_positive_rate_30d: float
    detection_latency_minutes: int
    explanation: str
    suggested_actions: list[str]
    series: list[TimeSeriesPoint]
    status: AnomalyAlertStatus = AnomalyAlertStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    acknowledged_at: datetime | None = None
    acknowledged_by: str | None = None
    dismissed_at: datetime | None = None
    dismissed_by: str | None = None

    def to_summary(self) -> dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "metric_name": self.metric_name,
            "domain": self.domain,
            "department_scope": self.department_scope,
            "region": self.region,
            "anomaly_timestamp": self.anomaly_timestamp,
            "deviation_percent": self.deviation_percent,
            "severity": self.severity.value,
            "status": self.status.value,
            "explanation": self.explanation,
            "false_positive_rate_30d": self.false_positive_rate_30d,
            "detection_latency_minutes": self.detection_latency_minutes,
            "created_at": self.created_at.isoformat(),
        }

    def to_detail(self) -> dict[str, Any]:
        return {
            **self.to_summary(),
            "isolation_forest_score": self.isolation_forest_score,
            "suggested_actions": list(self.suggested_actions),
            "series": [point.__dict__ for point in self.series],
            "confidence_state": "low-confidence",
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "dismissed_at": self.dismissed_at.isoformat() if self.dismissed_at else None,
            "dismissed_by": self.dismissed_by,
        }


class AnomalyDetectionService:
    def __init__(self) -> None:
        self._alerts: dict[str, AnomalyAlert] = {}

    def run_detection(
        self,
        *,
        metric_name: str,
        principal: JWTClaims,
        domain: str = "sales",
        region: str = "HCM",
    ) -> dict[str, Any]:
        alert = self._build_alert(metric_name=metric_name, department_scope=principal.department, domain=domain, region=region)
        self._alerts[alert.alert_id] = alert
        return {
            "scan_id": str(uuid4()),
            "status": "completed",
            "alerts_created": 1,
            "false_positive_rate_30d": alert.false_positive_rate_30d,
            "detection_latency_minutes": alert.detection_latency_minutes,
            "latest_alert_id": alert.alert_id,
        }

    def list_alerts(self, *, principal: JWTClaims) -> list[dict[str, Any]]:
        alerts = [alert for alert in self._alerts.values() if alert.department_scope == principal.department]
        return [alert.to_summary() for alert in sorted(alerts, key=lambda item: item.created_at, reverse=True)]

    def get_alert(self, *, alert_id: str, principal: JWTClaims) -> dict[str, Any]:
        alert = self._require_alert(alert_id=alert_id, principal=principal)
        return alert.to_detail()

    def acknowledge_alert(self, *, alert_id: str, principal: JWTClaims) -> dict[str, Any]:
        alert = self._require_alert(alert_id=alert_id, principal=principal)
        alert.status = AnomalyAlertStatus.ACKNOWLEDGED
        alert.acknowledged_at = datetime.now(UTC)
        alert.acknowledged_by = principal.sub
        return alert.to_detail()

    def dismiss_alert(self, *, alert_id: str, principal: JWTClaims) -> dict[str, Any]:
        alert = self._require_alert(alert_id=alert_id, principal=principal)
        alert.status = AnomalyAlertStatus.DISMISSED
        alert.dismissed_at = datetime.now(UTC)
        alert.dismissed_by = principal.sub
        return alert.to_detail()

    def reset(self) -> None:
        self._alerts.clear()

    def _require_alert(self, *, alert_id: str, principal: JWTClaims) -> AnomalyAlert:
        alert = self._alerts.get(alert_id)
        if alert is None:
            raise HTTPException(status_code=404, detail="Anomaly alert not found")
        if alert.department_scope != principal.department:
            raise HTTPException(status_code=403, detail="Anomaly alert is outside your permitted scope")
        return alert

    @staticmethod
    def _build_alert(*, metric_name: str, department_scope: str, domain: str, region: str) -> AnomalyAlert:
        series = [
            TimeSeriesPoint(timestamp="2026-03-12", actual=1240, expected_min=1180, expected_max=1320),
            TimeSeriesPoint(timestamp="2026-03-13", actual=1265, expected_min=1195, expected_max=1330),
            TimeSeriesPoint(timestamp="2026-03-14", actual=1215, expected_min=1170, expected_max=1305),
            TimeSeriesPoint(timestamp="2026-03-15", actual=780, expected_min=1185, expected_max=1310, is_anomaly=True),
            TimeSeriesPoint(timestamp="2026-03-16", actual=1230, expected_min=1180, expected_max=1315),
        ]
        return AnomalyAlert(
            alert_id=str(uuid4()),
            metric_name=metric_name,
            domain=domain,
            department_scope=department_scope,
            region=region,
            anomaly_timestamp="2026-03-15T09:00:00+07:00",
            deviation_percent=-40.0,
            severity=AlertSeverity.HIGH,
            isolation_forest_score=-0.22,
            false_positive_rate_30d=0.08,
            detection_latency_minutes=42,
            explanation="Đơn hàng khu vực HCM ngày 15/3 thấp hơn 40% so với dự kiến.",
            suggested_actions=[
                "Kiểm tra pipeline đơn hàng của khu vực HCM",
                "So sánh với chiến dịch bán hàng đang chạy",
                "Mở truy vấn drill-down theo kênh để xác minh nguồn giảm",
            ],
            series=series,
            status=AnomalyAlertStatus.ACTIVE,
        )


_anomaly_detection_service = AnomalyDetectionService()


def get_anomaly_detection_service() -> AnomalyDetectionService:
    return _anomaly_detection_service


def reset_anomaly_detection_service() -> None:
    _anomaly_detection_service.reset()
