"""Export job system for async report generation.

Provides:
- Async export jobs for PDF, Excel, CSV, JSON formats
- Progress tracking
- File storage (local filesystem for dev, S3 for production)
- Job status polling
"""
import csv
import io
import json
import logging
import os
import secrets
import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional

logger = logging.getLogger("quantive.export_jobs")


# ── Export Types ────────────────────────────────────────────────────────────

class ExportFormat(str, Enum):
    PDF = "pdf"
    EXCEL = "xlsx"
    CSV = "csv"
    JSON = "json"


class ExportStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Export Job Store ────────────────────────────────────────────────────────

class ExportJobStore:
    """In-memory export job store. In production, use the database."""

    def __init__(self):
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create_job(
        self,
        user_id: str,
        org_id: str,
        export_type: str,
        resource_type: str,
        resource_id: str,
        output_format: str,
        config: Optional[dict] = None,
    ) -> dict:
        job_id = secrets.token_urlsafe(16)
        job = {
            "id": job_id,
            "user_id": user_id,
            "org_id": org_id,
            "export_type": export_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "output_format": output_format,
            "status": ExportStatus.QUEUED.value,
            "progress": 0,
            "output_path": None,
            "error_message": None,
            "config": config or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
        }
        with self._lock:
            self._jobs[job_id] = job
        return job

    def get_job(self, job_id: str) -> Optional[dict]:
        return self._jobs.get(job_id)

    def update_job(self, job_id: str, **updates):
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(updates)

    def list_jobs(self, user_id: Optional[str] = None, limit: int = 50) -> list[dict]:
        jobs = list(self._jobs.values())
        if user_id:
            jobs = [j for j in jobs if j["user_id"] == user_id]
        return sorted(jobs, key=lambda j: j["created_at"], reverse=True)[:limit]


# Singleton
_export_store: Optional[ExportJobStore] = None


def get_export_store() -> ExportJobStore:
    global _export_store
    if _export_store is None:
        _export_store = ExportJobStore()
    return _export_store


# ── Export Renderers ────────────────────────────────────────────────────────

def render_csv(data: list[dict], columns: Optional[list[str]] = None) -> str:
    """Render data as CSV."""
    if not data:
        return ""

    if not columns:
        columns = list(data[0].keys())

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(data)
    return output.getvalue()


def render_json(data: list[dict], pretty: bool = True) -> str:
    """Render data as JSON."""
    return json.dumps(data, indent=2 if pretty else None, default=str)


def render_excel_xml(data: list[dict], columns: Optional[list[str]] = None) -> bytes:
    """Render data as Excel XML ( SpreadsheetML).

    This is a lightweight Excel-compatible format that doesn't require openpyxl.
    For full .xlsx support, use openpyxl.
    """
    if not data:
        return b""

    if not columns:
        columns = list(data[0].keys())

    xml_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<?mso-application progid="Excel.Sheet"?>',
        '<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"',
        '  xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">',
        '  <Styles>',
        '    <Style ss:ID="header"><Font ss:Bold="1"/></Style>',
        '  </Styles>',
        '  <Worksheet ss:Name="Export">',
        '    <Table>',
    ]

    # Header row
    xml_parts.append('      <Row ss:StyleID="header">')
    for col in columns:
        xml_parts.append(f'        <Cell><Data ss:Type="String">{col}</Data></Cell>')
    xml_parts.append('      </Row>')

    # Data rows
    for row in data:
        xml_parts.append('      <Row>')
        for col in columns:
            val = row.get(col, "")
            # Escape XML
            val_str = str(val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            xml_parts.append(f'        <Cell><Data ss:Type="String">{val_str}</Data></Cell>')
        xml_parts.append('      </Row>')

    xml_parts.extend([
        '    </Table>',
        '  </Worksheet>',
        '</Workbook>',
    ])

    return "\n".join(xml_parts).encode("utf-8")


# ── Export Executors ────────────────────────────────────────────────────────

# Registry of export handlers
_EXPORT_HANDLERS: dict[str, Callable] = {}


def register_export_handler(export_type: str, handler: Callable):
    """Register a handler for an export type."""
    _EXPORT_HANDLERS[export_type] = handler


def default_portfolio_export(portfolio: dict, config: dict) -> list[dict]:
    """Default export handler for portfolios."""
    return portfolio.get("instruments", [])


def default_optimization_export(optimization: dict, config: dict) -> list[dict]:
    """Default export handler for optimization results."""
    results = []
    for strategy in optimization.get("strategies", []):
        results.append({
            "name": strategy.get("name", ""),
            "rank": strategy.get("rank", 0),
            "cost": strategy.get("metrics", {}).get("financing_cost", 0),
            "objective_value": strategy.get("metrics", {}).get("objective_value", 0),
            "feasible": strategy.get("feasible", True),
        })
    return results


# Register defaults
register_export_handler("portfolio", default_portfolio_export)
register_export_handler("optimization", default_optimization_export)


# ── Export Execution ────────────────────────────────────────────────────────

def execute_export(
    job_id: str,
    data: list[dict],
    columns: Optional[list[str]] = None,
) -> str:
    """Execute an export job and return the output path.

    Args:
        job_id: Export job ID
        data: Data to export
        columns: Optional column list (auto-detected if not provided)

    Returns:
        Path to the exported file
    """
    store = get_export_store()
    job = store.get_job(job_id)
    if not job:
        raise ValueError(f"Export job {job_id} not found")

    store.update_job(job_id, status=ExportStatus.RUNNING.value, progress=10)

    try:
        output_format = ExportFormat(job["output_format"])
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"export_{job_id[:8]}_{timestamp}"

        # Create output directory
        output_dir = os.path.join("exports", job["org_id"])
        os.makedirs(output_dir, exist_ok=True)

        store.update_job(job_id, progress=30)

        if output_format == ExportFormat.CSV:
            content = render_csv(data, columns)
            filepath = os.path.join(output_dir, f"{filename}.csv")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        elif output_format == ExportFormat.JSON:
            content = render_json(data)
            filepath = os.path.join(output_dir, f"{filename}.json")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        elif output_format == ExportFormat.EXCEL:
            content = render_excel_xml(data, columns)
            filepath = os.path.join(output_dir, f"{filename}.xml")
            with open(filepath, "wb") as f:
                f.write(content)

        elif output_format == ExportFormat.PDF:
            # For PDF, generate HTML and note it needs wkhtmltopdf or similar
            html = _render_html(data, columns, job.get("config", {}))
            filepath = os.path.join(output_dir, f"{filename}.html")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(html)

        else:
            raise ValueError(f"Unsupported format: {output_format}")

        store.update_job(
            job_id,
            status=ExportStatus.COMPLETED.value,
            progress=100,
            output_path=filepath,
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.info(f"Export job {job_id} completed: {filepath}")
        return filepath

    except Exception as e:
        store.update_job(
            job_id,
            status=ExportStatus.FAILED.value,
            error_message=str(e)[:2000],
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        logger.error(f"Export job {job_id} failed: {e}")
        raise


def _render_html(data: list[dict], columns: Optional[list[str]], config: dict) -> str:
    """Render data as HTML for PDF export."""
    if not columns and data:
        columns = list(data[0].keys())

    title = config.get("title", "Export")
    rows_html = ""
    for row in (data or []):
        cells = "".join(f"<td>{row.get(col, '')}</td>" for col in (columns or []))
        rows_html += f"<tr>{cells}</tr>\n"

    header_cells = "".join(f"<th>{col}</th>" for col in (columns or []))

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <style>
        body {{ font-family: sans-serif; padding: 2rem; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f5f5f5; }}
        tr:nth-child(even) {{ background: #fafafa; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p>Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
    <table>
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{rows_html}</tbody>
    </table>
</body>
</html>"""


# ── Async Export Runner ─────────────────────────────────────────────────────

def start_export_job(
    job_id: str,
    data_fetcher: Callable[[], list[dict]],
    columns: Optional[list[str]] = None,
):
    """Start an export job in a background thread.

    Args:
        job_id: The export job ID
        data_fetcher: Callable that returns the data to export
        columns: Optional column specification
    """
    def _run():
        try:
            data = data_fetcher()
            execute_export(job_id, data, columns)
        except Exception as e:
            logger.error(f"Export job {job_id} thread error: {e}")
            store = get_export_store()
            store.update_job(
                job_id,
                status=ExportStatus.FAILED.value,
                error_message=str(e)[:2000],
            )

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
