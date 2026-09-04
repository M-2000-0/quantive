"""Model monitoring service — tracks prediction accuracy, drift, and performance."""
from __future__ import annotations

import logging
import math
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import ModelVersion
from app.migrations import _ensure_table_exists

logger = logging.getLogger("quantive.ai.model_monitor")


def record_prediction(
    db: Session,
    model_name: str,
    predicted: float,
    actual: float,
    prediction_type: str = "default",
) -> dict:
    """Record a prediction vs actual outcome for drift tracking."""
    _ensure_table_exists(db, "prediction_drift", """
        CREATE TABLE IF NOT EXISTS prediction_drift (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            prediction_type TEXT NOT NULL DEFAULT 'default',
            mean_predicted REAL,
            mean_actual REAL,
            drift_score REAL,
            sample_size INTEGER DEFAULT 1,
            recorded_at TEXT
        )
    """)

    drift_score = abs(predicted - actual) / max(abs(actual), 1e-10)

    db.execute(
        __import__("sqlalchemy").text(
            """INSERT INTO prediction_drift
               (model_name, prediction_type, mean_predicted, mean_actual, drift_score, sample_size, recorded_at)
               VALUES (:model, :ptype, :pred, :actual, :drift, 1, :now)"""
        ),
        {
            "model": model_name,
            "ptype": prediction_type,
            "pred": predicted,
            "actual": actual,
            "drift": drift_score,
            "now": datetime.now(timezone.utc).isoformat(),
        },
    )
    db.commit()

    return {
        "model_name": model_name,
        "predicted": predicted,
        "actual": actual,
        "drift_score": drift_score,
    }


def get_model_performance(
    db: Session,
    model_name: Optional[str] = None,
    hours: int = 168,
) -> dict:
    """Get model performance metrics over a time window."""
    from datetime import timedelta

    _ensure_table_exists(db, "prediction_drift", """
        CREATE TABLE IF NOT EXISTS prediction_drift (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            prediction_type TEXT NOT NULL DEFAULT 'default',
            mean_predicted REAL,
            mean_actual REAL,
            drift_score REAL,
            sample_size INTEGER DEFAULT 1,
            recorded_at TEXT
        )
    """)

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

    query = "SELECT model_name, AVG(drift_score), AVG(mean_predicted), AVG(mean_actual), COUNT(*) FROM prediction_drift WHERE recorded_at >= :cutoff"
    params = {"cutoff": cutoff}
    if model_name:
        query += " AND model_name = :model"
        params["model"] = model_name
    query += " GROUP BY model_name"

    rows = db.execute(__import__("sqlalchemy").text(query), params).fetchall()

    models = []
    for row in rows:
        name, avg_drift, avg_pred, avg_actual, count = row
        models.append({
            "model_name": name,
            "avg_drift_score": round(avg_drift or 0, 4),
            "avg_predicted": round(avg_pred or 0, 4),
            "avg_actual": round(avg_actual or 0, 4),
            "sample_count": count,
            "accuracy_pct": round(max(0, 100 - (avg_drift or 0) * 100), 1),
        })

    # Get active model versions
    active_models = db.query(ModelVersion).filter(ModelVersion.is_active == True).all()
    active_versions = [{
        "model_name": m.model_name,
        "version": m.version,
        "validation_accuracy": float(m.validation_accuracy) if m.validation_accuracy else None,
    } for m in active_models]

    return {
        "period_hours": hours,
        "models": models,
        "active_versions": active_versions,
        "total_predictions": sum(m["sample_count"] for m in models),
    }


def check_drift_alerts(
    db: Session,
    drift_threshold: float = 0.3,
    min_samples: int = 10,
) -> list[dict]:
    """Check for model drift alerts — returns models exceeding drift threshold."""
    from datetime import timedelta

    _ensure_table_exists(db, "prediction_drift", """
        CREATE TABLE IF NOT EXISTS prediction_drift (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            prediction_type TEXT NOT NULL DEFAULT 'default',
            mean_predicted REAL,
            mean_actual REAL,
            drift_score REAL,
            sample_size INTEGER DEFAULT 1,
            recorded_at TEXT
        )
    """)

    cutoff = (datetime.now(timezone.utc) - timedelta(hours=168)).isoformat()
    rows = db.execute(
        __import__("sqlalchemy").text(
            """SELECT model_name, AVG(drift_score), COUNT(*)
               FROM prediction_drift
               WHERE recorded_at >= :cutoff
               GROUP BY model_name
               HAVING COUNT(*) >= :min_samples"""
        ),
        {"cutoff": cutoff, "min_samples": min_samples},
    ).fetchall()

    alerts = []
    for row in rows:
        name, avg_drift, count = row
        if avg_drift and avg_drift > drift_threshold:
            alerts.append({
                "model_name": name,
                "avg_drift_score": round(avg_drift, 4),
                "sample_count": count,
                "severity": "critical" if avg_drift > 0.5 else "warning",
                "message": f"Model '{name}' drift score {avg_drift:.2%} exceeds threshold {drift_threshold:.2%}. "
                          f"Consider retraining with fresh data.",
            })

    return alerts


def get_drift_history(
    db: Session,
    model_name: str,
    limit: int = 100,
) -> list[dict]:
    """Get drift history for a specific model."""
    _ensure_table_exists(db, "prediction_drift", """
        CREATE TABLE IF NOT EXISTS prediction_drift (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            model_name TEXT NOT NULL,
            prediction_type TEXT NOT NULL DEFAULT 'default',
            mean_predicted REAL,
            mean_actual REAL,
            drift_score REAL,
            sample_size INTEGER DEFAULT 1,
            recorded_at TEXT
        )
    """)

    rows = db.execute(
        __import__("sqlalchemy").text(
            """SELECT model_name, prediction_type, mean_predicted, mean_actual, drift_score, recorded_at
               FROM prediction_drift
               WHERE model_name = :model
               ORDER BY recorded_at DESC
               LIMIT :limit"""
        ),
        {"model": model_name, "limit": limit},
    ).fetchall()

    return [{
        "model_name": row[0],
        "prediction_type": row[1],
        "mean_predicted": row[2],
        "mean_actual": row[3],
        "drift_score": row[4],
        "recorded_at": row[5],
    } for row in rows]
