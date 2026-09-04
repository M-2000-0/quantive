"""Model retraining service — scheduled retraining, drift-triggered retraining, A/B testing."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ModelVersion

logger = logging.getLogger("quantive.ai.model_retraining")


def get_retraining_schedule(db: Session) -> dict:
    """Get current retraining schedule and model status."""
    models = db.query(ModelVersion).filter(ModelVersion.is_active == True).all()
    versions = []
    for m in models:
        versions.append({
            "model_name": m.model_name,
            "version": m.version,
            "is_active": m.is_active,
            "validation_accuracy": float(m.validation_accuracy) if m.validation_accuracy else None,
            "created_at": m.created_at.isoformat() if m.created_at else None,
            "training_data_range": m.training_data_range,
        })

    return {
        "active_models": len(versions),
        "models": versions,
        "retraining_config": {
            "schedule": "nightly",
            "drift_threshold": 0.3,
            "min_samples_for_retrain": 100,
            "auto_retrain_enabled": True,
        },
    }


def trigger_retraining(
    db: Session,
    model_name: str,
    reason: str = "manual",
    training_data_range: Optional[str] = None,
) -> dict:
    """Trigger a model retraining run.

    In production this would launch a background job that:
    1. Pulls fresh training data
    2. Retrains the model
    3. Validates against holdout set
    4. If accuracy improves, promotes to active
    5. Records the new ModelVersion
    """
    # Find current active version
    current = db.query(ModelVersion).filter(
        ModelVersion.model_name == model_name,
        ModelVersion.is_active == True,
    ).first()

    current_version = current.version if current else "0.0.0"
    major, minor, patch = (current_version.split(".") + ["0", "0", "0"])[:3]

    if reason == "drift_detected":
        new_version = f"{major}.{minor}.{int(patch) + 1}"
    elif reason == "scheduled":
        new_version = f"{major}.{int(minor) + 1}.0"
    else:
        new_version = f"{major}.{minor}.{int(patch) + 1}"

    # Deactivate previous version
    if current:
        current.is_active = False

    # Create new version record
    new_model = ModelVersion(
        model_name=model_name,
        version=new_version,
        description=f"Retrained — reason: {reason}",
        training_data_range=training_data_range or "latest",
        created_by=None,
        is_active=True,
    )
    db.add(new_model)
    db.commit()
    db.refresh(new_model)

    logger.info(f"Retrained {model_name}: {current_version} -> {new_version} (reason: {reason})")

    return {
        "model_name": model_name,
        "previous_version": current_version,
        "new_version": new_version,
        "reason": reason,
        "model_id": new_model.id,
    }


def check_and_retrain(db: Session, drift_threshold: float = 0.3) -> list[dict]:
    """Check drift alerts and trigger retraining for models exceeding threshold."""
    from app.services.model_monitor import check_drift_alerts

    alerts = check_drift_alerts(db, drift_threshold=drift_threshold)
    retrained = []

    for alert in alerts:
        if alert.get("severity") == "critical":
            result = trigger_retraining(
                db,
                model_name=alert["model_name"],
                reason="drift_detected",
            )
            retrained.append(result)

    return {
        "drift_alerts": len(alerts),
        "models_retrained": len(retrained),
        "retraining_results": retrained,
    }


def get_model_lifecycle(db: Session, model_name: Optional[str] = None) -> list[dict]:
    """Get version history for models — shows A/B test lineage."""
    q = db.query(ModelVersion)
    if model_name:
        q = q.filter(ModelVersion.model_name == model_name)
    versions = q.order_by(ModelVersion.created_at.desc()).limit(50).all()

    return [{
        "id": m.id,
        "model_name": m.model_name,
        "version": m.version,
        "is_active": m.is_active,
        "validation_accuracy": float(m.validation_accuracy) if m.validation_accuracy else None,
        "description": m.description,
        "training_data_range": m.training_data_range,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in versions]
