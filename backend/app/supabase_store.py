from __future__ import annotations

import os
import re
from typing import Any
import httpx
from fastapi import HTTPException

from . import db

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_TABLE = os.getenv("PRESSURE_ROOM_SUPABASE_TABLE", "pressure_room_projects")
HTTP_TIMEOUT = 15.0
_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def configuration_error() -> str | None:
    if not SUPABASE_URL and not SUPABASE_SERVICE_ROLE_KEY:
        return None
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        return "Supabase requires both SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY."
    if not SUPABASE_URL.startswith("https://"):
        return "SUPABASE_URL must use HTTPS."
    if not _TABLE_RE.fullmatch(SUPABASE_TABLE):
        return "PRESSURE_ROOM_SUPABASE_TABLE contains invalid characters."
    return None


def storage_mode() -> str:
    return "supabase-postgres" if enabled() else "sqlite-cache"


def _sub(session: dict) -> str:
    sub = str(session.get("sub", "")).strip()
    if not sub:
        raise HTTPException(401, "Google account identity is missing. Connect Google Drive again.")
    return sub


def _headers(*, prefer: str | None = None) -> dict[str, str]:
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request(method: str, *, params: dict[str, Any] | None = None, json: Any = None, prefer: str | None = None) -> httpx.Response:
    try:
        response = httpx.request(
            method,
            f"{SUPABASE_URL}/rest/v1/{SUPABASE_TABLE}",
            params=params,
            json=json,
            headers=_headers(prefer=prefer),
            timeout=HTTP_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Durable story storage is temporarily unavailable. Your edit was not committed.") from exc
    if response.status_code >= 400:
        detail = ""
        try:
            payload = response.json()
            detail = str(payload.get("message") or payload.get("hint") or "")
        except Exception:
            pass
        suffix = f" ({detail[:180]})" if detail else ""
        raise HTTPException(503, f"Supabase durable storage rejected the request{suffix}")
    return response


def ping() -> None:
    if not enabled():
        return
    _request("GET", params={"select": "project_id", "limit": "1"})


def _row(session: dict, project_id: str) -> dict:
    payload = db.project_payload(project_id, include_snapshots=True)
    return {
        "user_sub": _sub(session),
        "project_id": project_id,
        "payload": payload,
        "revision": db.project_revision(project_id),
        "sync_state": db.sync_job(project_id),
        "updated_at": db.now_iso(),
    }


def save_project(session: dict, project_id: str, *, expected_revision: str | None = None) -> dict:
    """Persist one committed-intent snapshot with optimistic concurrency."""
    if not enabled():
        return {"stored": False}
    row = _row(session, project_id)
    if expected_revision:
        response = _request(
            "PATCH",
            params={
                "user_sub": f"eq.{_sub(session)}",
                "project_id": f"eq.{project_id}",
                "revision": f"eq.{expected_revision}",
                "select": "project_id,revision",
            },
            json={"payload": row["payload"], "revision": row["revision"], "sync_state": row["sync_state"], "updated_at": row["updated_at"]},
            prefer="return=representation",
        )
        records = response.json() if response.content else []
        if not records:
            raise HTTPException(409, {"code": "stale_story", "message": "This story changed on another device. Your draft is still on this page; reload the story before saving again."})
        return {"stored": True, "revision": row["revision"]}

    _request(
        "POST",
        params={"on_conflict": "user_sub,project_id"},
        json=[row],
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return {"stored": True, "revision": row["revision"]}


def list_projects(session: dict) -> list[dict]:
    if not enabled():
        return []
    response = _request(
        "GET",
        params={
            "select": "project_id,payload,revision,sync_state,updated_at",
            "user_sub": f"eq.{_sub(session)}",
            "order": "updated_at.asc",
        },
    )
    data = response.json()
    if not isinstance(data, list):
        raise HTTPException(502, "Supabase returned an invalid workspace response.")
    return data


def _restore_sync_state(project_id: str, state: Any) -> None:
    if not isinstance(state, dict):
        return
    allowed = {"file_id", "etag", "operation_id", "payload_json", "stage", "status", "error"}
    fields = {key: state.get(key) for key in allowed if key in state}
    if fields:
        db.set_sync(project_id, **fields)


def save_sync_state(session: dict, project_id: str, *, story_revision: str | None = None) -> bool:
    """Update Drive mirror metadata without ever overwriting newer story content."""
    if not enabled():
        return False
    revision = story_revision or db.project_revision(project_id)
    response = _request(
        "PATCH",
        params={
            "user_sub": f"eq.{_sub(session)}",
            "project_id": f"eq.{project_id}",
            "revision": f"eq.{revision}",
            "select": "project_id",
        },
        json={"sync_state": db.sync_job(project_id)},
        prefer="return=representation",
    )
    records = response.json() if response.content else []
    return bool(records)


def hydrate_user(session: dict) -> dict:
    """Make the local working cache reflect durable Postgres state."""
    if not enabled():
        return {"pulled": 0, "remote": 0}
    records = list_projects(session)
    pulled = 0
    with db.transaction():
        for record in records:
            payload = record.get("payload")
            project_id = str(record.get("project_id") or "")
            if not project_id or not isinstance(payload, dict) or payload.get("project", {}).get("id") != project_id:
                raise HTTPException(502, "Supabase contains an invalid Pressure Room project row.")
            local = db.one("SELECT id FROM projects WHERE id=?", [project_id])
            local_revision = db.project_revision(project_id) if local else None
            if local_revision != record.get("revision"):
                db.import_payload(payload, mode="replace")
                _restore_sync_state(project_id, record.get("sync_state"))
                pulled += 1
                continue
            local_job = db.sync_job(project_id)
            remote_job = record.get("sync_state") if isinstance(record.get("sync_state"), dict) else None
            if remote_job and (not local_job or str(remote_job.get("updated_at") or "") >= str(local_job.get("updated_at") or "")):
                _restore_sync_state(project_id, remote_job)
    return {"pulled": pulled, "remote": len(records)}


def save_all(session: dict) -> int:
    if not enabled():
        return 0
    count = 0
    for project in db.get_projects():
        save_project(session, project["id"])
        count += 1
    return count
