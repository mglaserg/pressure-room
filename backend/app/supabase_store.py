from __future__ import annotations

import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from fastapi import HTTPException

from . import db

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")
SUPABASE_TABLE = os.getenv("PRESSURE_ROOM_SUPABASE_TABLE", "pressure_room_projects")
HTTP_TIMEOUT = 15.0
_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ROLE_ORDER = {"viewer": 0, "editor": 1, "owner": 2}
_LEGACY_CLAIMS: set[tuple[str, str]] = set()


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def auth_mode() -> bool:
    return _flag("PRESSURE_ROOM_AUTH_ENABLED")


def enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_SECRET_KEY)


def configuration_error() -> str | None:
    if not SUPABASE_URL and not SUPABASE_SECRET_KEY:
        return None
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        return "Supabase requires both SUPABASE_URL and SUPABASE_SECRET_KEY."
    if SUPABASE_SECRET_KEY.startswith("sb_publishable_"):
        return "SUPABASE_SECRET_KEY must be a server-side sb_secret_... key; publishable keys cannot back Pressure Room durable writes."
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
        label = "Supabase user identity" if auth_mode() else "Google account identity"
        raise HTTPException(401, f"{label} is missing. Sign in again.")
    return sub


def _email(session: dict) -> str:
    return str(session.get("email") or "").strip().lower()


def _headers(*, prefer: str | None = None) -> dict[str, str]:
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    headers = {
        "apikey": SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    return headers


def _request_table(
    table: str,
    method: str,
    *,
    params: dict[str, Any] | None = None,
    json: Any = None,
    prefer: str | None = None,
) -> httpx.Response:
    if not _TABLE_RE.fullmatch(table):
        raise HTTPException(500, "Invalid Supabase table configuration.")
    try:
        response = httpx.request(
            method,
            f"{SUPABASE_URL}/rest/v1/{table}",
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
            detail = str(payload.get("message") or payload.get("hint") or payload.get("details") or "")
        except Exception:
            pass
        suffix = f" ({detail[:180]})" if detail else ""
        raise HTTPException(503, f"Supabase durable storage rejected the request{suffix}")
    return response


def _request(method: str, *, params: dict[str, Any] | None = None, json: Any = None, prefer: str | None = None) -> httpx.Response:
    return _request_table(SUPABASE_TABLE, method, params=params, json=json, prefer=prefer)


def ping() -> None:
    if not enabled():
        return
    _request("GET", params={"select": "project_id", "limit": "1"})
    if auth_mode():
        _request_table("project_members", "GET", params={"select": "project_id", "limit": "1"})


def _project_meta(project_id: str) -> dict | None:
    response = _request(
        "GET",
        params={
            "select": "user_sub,project_id,owner_id,created_by,updated_by,revision,trashed_at",
            "project_id": f"eq.{project_id}",
            "limit": "2",
        },
    )
    rows = response.json() if response.content else []
    if not rows:
        return None
    if len(rows) > 1:
        raise HTTPException(409, "This story ID exists in more than one durable workspace. Import it as a copy before editing.")
    return rows[0]


def _upsert_member(project_id: str, session: dict, role: str) -> None:
    if role not in _ROLE_ORDER:
        raise ValueError("Invalid project role")
    current_response = _request_table(
        "project_members",
        "GET",
        params={
            "select": "role,created_at",
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{_sub(session)}",
            "limit": "1",
        },
    )
    current_rows = current_response.json() if current_response.content else []
    current = current_rows[0] if current_rows else None
    if current and _ROLE_ORDER.get(str(current.get("role")), -1) > _ROLE_ORDER[role]:
        role = str(current["role"])
    row = {
        "project_id": project_id,
        "user_id": _sub(session),
        "email": _email(session) or None,
        "role": role,
        "created_at": (current or {}).get("created_at") or db.now_iso(),
    }
    _request_table(
        "project_members",
        "POST",
        params={"on_conflict": "project_id,user_id"},
        json=[row],
        prefer="resolution=merge-duplicates,return=minimal",
    )


def role_for(session: dict, project_id: str) -> str | None:
    if not auth_mode():
        return "owner"
    meta = _project_meta(project_id)
    if not meta or meta.get("trashed_at"):
        return None
    response = _request_table(
        "project_members",
        "GET",
        params={
            "select": "role",
            "project_id": f"eq.{project_id}",
            "user_id": f"eq.{_sub(session)}",
            "limit": "1",
        },
    )
    rows = response.json() if response.content else []
    if rows:
        return rows[0].get("role")
    if str(meta.get("owner_id") or "") == _sub(session):
        _upsert_member(project_id, session, "owner")
        return "owner"
    return None


def require_role(session: dict, project_id: str, minimum: str = "viewer") -> str:
    if minimum not in _ROLE_ORDER:
        raise ValueError("Invalid minimum role")
    role = role_for(session, project_id)
    if role is None:
        raise HTTPException(404, "Project not found")
    if _ROLE_ORDER.get(role, -1) < _ROLE_ORDER[minimum]:
        raise HTTPException(403, f"This project requires {minimum} access.")
    return role


def can_manage_drive(session: dict, project_id: str) -> bool:
    """Only owners mirror shared stories; a brand-new unsaved project belongs to its creator."""
    if not auth_mode():
        return True
    meta = _project_meta(project_id)
    if not meta:
        return True
    return role_for(session, project_id) == "owner"


def _row(session: dict, project_id: str, meta: dict | None = None) -> dict:
    payload = db.project_payload(project_id, include_snapshots=True)
    owner_id = str((meta or {}).get("owner_id") or _sub(session))
    storage_sub = str((meta or {}).get("user_sub") or owner_id)
    return {
        "user_sub": storage_sub,
        "project_id": project_id,
        "payload": payload,
        "revision": db.project_revision(project_id),
        "sync_state": db.sync_job(project_id),
        "owner_id": owner_id if auth_mode() else (meta or {}).get("owner_id"),
        "created_by": (meta or {}).get("created_by") or (owner_id if auth_mode() else None),
        "updated_by": _sub(session) if auth_mode() else (meta or {}).get("updated_by"),
        "updated_at": db.now_iso(),
    }


def save_project(session: dict, project_id: str, *, expected_revision: str | None = None) -> dict:
    """Persist one committed-intent snapshot with optimistic concurrency."""
    if not enabled():
        return {"stored": False}

    # Legacy Google-auth storage path remains unchanged until magic-link auth is enabled.
    if not auth_mode():
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

    meta = _project_meta(project_id)
    if meta and meta.get("trashed_at"):
        raise HTTPException(409, "This project is in Trash. Restore it before editing.")
    if meta:
        require_role(session, project_id, "editor")
    row = _row(session, project_id, meta)

    if expected_revision and meta:
        response = _request(
            "PATCH",
            params={
                "user_sub": f"eq.{meta['user_sub']}",
                "project_id": f"eq.{project_id}",
                "revision": f"eq.{expected_revision}",
                "select": "project_id,revision",
            },
            json={
                "payload": row["payload"],
                "revision": row["revision"],
                "sync_state": row["sync_state"],
                "updated_by": _sub(session),
                "updated_at": row["updated_at"],
            },
            prefer="return=representation",
        )
        records = response.json() if response.content else []
        if not records:
            raise HTTPException(409, {"code": "stale_story", "message": "This story changed on another device. Your draft is still on this page; reload the story before saving again."})
        return {"stored": True, "revision": row["revision"]}

    if meta:
        _request(
            "PATCH",
            params={"user_sub": f"eq.{meta['user_sub']}", "project_id": f"eq.{project_id}"},
            json={
                "payload": row["payload"],
                "revision": row["revision"],
                "sync_state": row["sync_state"],
                "updated_by": _sub(session),
                "updated_at": row["updated_at"],
            },
            prefer="return=minimal",
        )
    else:
        _request(
            "POST",
            json=[row],
            prefer="return=minimal",
        )
        _upsert_member(project_id, session, "owner")
    return {"stored": True, "revision": row["revision"]}


def _records_for_project_ids(project_ids: list[str]) -> list[dict]:
    records: list[dict] = []
    for project_id in project_ids:
        response = _request(
            "GET",
            params={
                "select": "project_id,payload,revision,sync_state,updated_at,owner_id,created_by,updated_by,trashed_at",
                "project_id": f"eq.{project_id}",
                "trashed_at": "is.null",
                "limit": "2",
            },
        )
        rows = response.json() if response.content else []
        if len(rows) > 1:
            raise HTTPException(409, "A shared story ID is ambiguous in durable storage.")
        records.extend(rows)
    return records


def list_projects(session: dict) -> list[dict]:
    if not enabled():
        return []
    if not auth_mode():
        response = _request(
            "GET",
            params={
                "select": "project_id,payload,revision,sync_state,updated_at",
                "user_sub": f"eq.{_sub(session)}",
                "trashed_at": "is.null",
                "order": "updated_at.asc",
            },
        )
        data = response.json()
        if not isinstance(data, list):
            raise HTTPException(502, "Supabase returned an invalid workspace response.")
        return data

    owned_response = _request(
        "GET",
        params={
            "select": "project_id,payload,revision,sync_state,updated_at,owner_id,created_by,updated_by,trashed_at",
            "owner_id": f"eq.{_sub(session)}",
            "trashed_at": "is.null",
            "order": "updated_at.asc",
        },
    )
    owned = owned_response.json() if owned_response.content else []
    member_response = _request_table(
        "project_members",
        "GET",
        params={"select": "project_id,role", "user_id": f"eq.{_sub(session)}"},
    )
    memberships = member_response.json() if member_response.content else []
    owned_ids = {row.get("project_id") for row in owned}
    shared_ids = [str(row.get("project_id")) for row in memberships if row.get("project_id") and row.get("project_id") not in owned_ids]
    shared = _records_for_project_ids(shared_ids)
    data = [*owned, *shared]
    data.sort(key=lambda row: str(row.get("updated_at") or ""))
    return data


def claim_legacy_workspace(session: dict, google_session: dict | None) -> int:
    """Move a pre-magic-link Google partition to the authenticated Supabase user once."""
    if not (enabled() and auth_mode() and google_session):
        return 0
    auth_sub = _sub(session)
    google_sub = str(google_session.get("sub") or "").strip()
    if not google_sub or google_sub == auth_sub:
        return 0
    auth_email = _email(session)
    google_email = str(google_session.get("email") or "").strip().lower()
    if auth_email and google_email and auth_email != google_email:
        return 0
    key = (auth_sub, google_sub)
    if key in _LEGACY_CLAIMS:
        return 0
    response = _request(
        "GET",
        params={
            "select": "user_sub,project_id,owner_id",
            "user_sub": f"eq.{google_sub}",
        },
    )
    rows = response.json() if response.content else []
    claimed = 0
    for row in rows:
        project_id = str(row.get("project_id") or "")
        owner = str(row.get("owner_id") or "")
        if not project_id or (owner and owner != auth_sub):
            continue
        existing = _request(
            "GET",
            params={"select": "user_sub", "user_sub": f"eq.{auth_sub}", "project_id": f"eq.{project_id}", "limit": "1"},
        ).json()
        if existing:
            _upsert_member(project_id, session, "owner")
            continue
        _request(
            "PATCH",
            params={"user_sub": f"eq.{google_sub}", "project_id": f"eq.{project_id}"},
            json={
                "user_sub": auth_sub,
                "owner_id": auth_sub,
                "created_by": auth_sub,
                "updated_by": auth_sub,
                "updated_at": db.now_iso(),
            },
            prefer="return=minimal",
        )
        _upsert_member(project_id, session, "owner")
        claimed += 1
    _LEGACY_CLAIMS.add(key)
    return claimed


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
    meta = _project_meta(project_id)
    if auth_mode():
        require_role(session, project_id, "editor")
    params = {
        "project_id": f"eq.{project_id}",
        "revision": f"eq.{revision}",
        "select": "project_id",
    }
    if meta:
        params["user_sub"] = f"eq.{meta['user_sub']}"
    elif not auth_mode():
        params["user_sub"] = f"eq.{_sub(session)}"
    response = _request(
        "PATCH",
        params=params,
        json={"sync_state": db.sync_job(project_id)},
        prefer="return=representation",
    )
    records = response.json() if response.content else []
    return bool(records)


def hydrate_user(session: dict) -> dict:
    """Make the local working cache reflect durable Postgres state visible to this user."""
    if not enabled():
        return {"pulled": 0, "remote": 0}
    records = list_projects(session)
    pulled = 0
    remote_ids = {str(record.get("project_id") or "") for record in records}
    with db.transaction():
        if auth_mode():
            for local_project in db.get_projects():
                if local_project["id"] not in remote_ids:
                    db.delete("projects", local_project["id"])
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
        # Shared viewer caches can contain projects they are not allowed to rewrite.
        if auth_mode() and role_for(session, project["id"]) not in {"owner", "editor"}:
            continue
        save_project(session, project["id"])
        count += 1
    return count


# ---- Project lifecycle -----------------------------------------------------------------

def _owner_meta(session: dict, project_id: str, *, allow_trashed: bool = True) -> dict:
    meta = _project_meta(project_id)
    if not meta or str(meta.get("owner_id") or "") != _sub(session):
        raise HTTPException(404, "Project not found")
    if not allow_trashed and meta.get("trashed_at"):
        raise HTTPException(404, "Project not found")
    return meta


def list_trashed_projects(session: dict) -> list[dict]:
    if not (enabled() and auth_mode()):
        return []
    response = _request(
        "GET",
        params={
            "select": "project_id,payload,trashed_at,updated_at",
            "owner_id": f"eq.{_sub(session)}",
            "trashed_at": "not.is.null",
            "order": "trashed_at.desc",
        },
    )
    rows = response.json() if response.content else []
    result = []
    for row in rows:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        project = payload.get("project") if isinstance(payload.get("project"), dict) else {}
        result.append({
            "id": row.get("project_id"),
            "title": project.get("title") or "Untitled Story",
            "trashed_at": row.get("trashed_at"),
            "updated_at": row.get("updated_at"),
        })
    return result


def trash_project(session: dict, project_id: str) -> None:
    meta = _owner_meta(session, project_id, allow_trashed=False)
    _request(
        "PATCH",
        params={"user_sub": f"eq.{meta['user_sub']}", "project_id": f"eq.{project_id}"},
        json={"trashed_at": db.now_iso(), "updated_by": _sub(session), "updated_at": db.now_iso()},
        prefer="return=minimal",
    )
    record_event(session, project_id, "project.trashed", {})
    _request_table("project_presence", "DELETE", params={"project_id": f"eq.{project_id}"}, prefer="return=minimal")


def restore_project(session: dict, project_id: str) -> None:
    meta = _owner_meta(session, project_id)
    if not meta.get("trashed_at"):
        raise HTTPException(409, "Project is not in Trash.")
    _request(
        "PATCH",
        params={"user_sub": f"eq.{meta['user_sub']}", "project_id": f"eq.{project_id}"},
        json={"trashed_at": None, "updated_by": _sub(session), "updated_at": db.now_iso()},
        prefer="return=minimal",
    )
    _upsert_member(project_id, session, "owner")
    record_event(session, project_id, "project.restored", {})


def permanently_delete_project(session: dict, project_id: str) -> None:
    meta = _owner_meta(session, project_id)
    if not meta.get("trashed_at"):
        raise HTTPException(409, "Move the project to Trash before deleting it permanently.")
    for table in ("project_presence", "project_invites", "project_events", "project_members"):
        _request_table(table, "DELETE", params={"project_id": f"eq.{project_id}"}, prefer="return=minimal")
    _request(
        "DELETE",
        params={"user_sub": f"eq.{meta['user_sub']}", "project_id": f"eq.{project_id}"},
        prefer="return=minimal",
    )


# ---- Sharing / collaboration metadata -------------------------------------------------

def list_members(session: dict, project_id: str) -> dict:
    role = require_role(session, project_id, "viewer")
    members_response = _request_table(
        "project_members",
        "GET",
        params={"select": "user_id,email,role,created_at", "project_id": f"eq.{project_id}", "order": "created_at.asc"},
    )
    members = members_response.json() if members_response.content else []
    invites: list[dict] = []
    if role == "owner":
        invite_response = _request_table(
            "project_invites",
            "GET",
            params={
                "select": "id,email,role,created_at,expires_at,accepted_at",
                "project_id": f"eq.{project_id}",
                "accepted_at": "is.null",
                "order": "created_at.desc",
            },
        )
        invites = invite_response.json() if invite_response.content else []
    return {"role": role, "members": members, "invites": invites}


def create_invite(session: dict, project_id: str, email: str, role: str) -> str:
    require_role(session, project_id, "owner")
    if role not in {"editor", "viewer"}:
        raise HTTPException(400, "Invite role must be editor or viewer.")
    email = str(email or "").strip().lower()
    if not email or "@" not in email or len(email) > 320:
        raise HTTPException(400, "Enter a valid collaborator email.")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    invite_id = db.uid()
    _request_table(
        "project_invites",
        "POST",
        json=[{
            "id": invite_id,
            "project_id": project_id,
            "email": email,
            "role": role,
            "token_hash": token_hash,
            "invited_by": _sub(session),
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=7)).isoformat(),
        }],
        prefer="return=minimal",
    )
    record_event(session, project_id, "project.invited", {"email": email, "role": role})
    return token


def accept_invite(session: dict, token: str) -> dict:
    token = str(token or "").strip()
    if not token:
        raise HTTPException(400, "Invite token is missing.")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    response = _request_table(
        "project_invites",
        "GET",
        params={
            "select": "id,project_id,email,role,expires_at,accepted_at",
            "token_hash": f"eq.{token_hash}",
            "limit": "1",
        },
    )
    rows = response.json() if response.content else []
    if not rows:
        raise HTTPException(404, "This invitation is invalid or has already been removed.")
    invite = rows[0]
    if invite.get("accepted_at"):
        raise HTTPException(409, "This invitation has already been accepted.")
    if str(invite.get("email") or "").lower() != _email(session):
        raise HTTPException(403, "Sign in with the email address this invitation was sent to.")
    try:
        expires = datetime.fromisoformat(str(invite["expires_at"]).replace("Z", "+00:00"))
    except Exception:
        raise HTTPException(410, "This invitation has expired.")
    if expires <= datetime.now(timezone.utc):
        raise HTTPException(410, "This invitation has expired.")
    project_id = str(invite["project_id"])
    _upsert_member(project_id, session, str(invite["role"]))
    _request_table(
        "project_invites",
        "PATCH",
        params={"id": f"eq.{invite['id']}"},
        json={"accepted_at": db.now_iso(), "accepted_by": _sub(session)},
        prefer="return=minimal",
    )
    record_event(session, project_id, "project.invite_accepted", {"email": _email(session), "role": invite["role"]})
    return {"project_id": project_id, "role": invite["role"]}


def remove_member(session: dict, project_id: str, user_id: str) -> None:
    require_role(session, project_id, "owner")
    meta = _project_meta(project_id)
    if meta and str(meta.get("owner_id") or "") == str(user_id):
        raise HTTPException(400, "The project owner cannot be removed.")
    _request_table(
        "project_members",
        "DELETE",
        params={"project_id": f"eq.{project_id}", "user_id": f"eq.{user_id}"},
        prefer="return=minimal",
    )
    _request_table(
        "project_presence",
        "DELETE",
        params={"project_id": f"eq.{project_id}", "user_id": f"eq.{user_id}"},
        prefer="return=minimal",
    )
    record_event(session, project_id, "project.member_removed", {"user_id": user_id})


def heartbeat(session: dict, project_id: str) -> list[dict]:
    require_role(session, project_id, "viewer")
    row = {
        "project_id": project_id,
        "user_id": _sub(session),
        "email": _email(session) or None,
        "seen_at": db.now_iso(),
    }
    _request_table(
        "project_presence",
        "POST",
        params={"on_conflict": "project_id,user_id"},
        json=[row],
        prefer="resolution=merge-duplicates,return=minimal",
    )
    return presence(session, project_id)


def presence(session: dict, project_id: str) -> list[dict]:
    require_role(session, project_id, "viewer")
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=45)).isoformat()
    response = _request_table(
        "project_presence",
        "GET",
        params={
            "select": "user_id,email,seen_at",
            "project_id": f"eq.{project_id}",
            "seen_at": f"gte.{cutoff}",
            "order": "seen_at.desc",
        },
    )
    return response.json() if response.content else []


def record_event(session: dict, project_id: str, kind: str, payload: dict | None = None) -> None:
    if not (enabled() and auth_mode()):
        return
    role = role_for(session, project_id)
    if not role:
        return
    _request_table(
        "project_events",
        "POST",
        json=[{
            "id": db.uid(),
            "project_id": project_id,
            "actor_id": _sub(session),
            "actor_email": _email(session) or None,
            "kind": str(kind)[:80],
            "payload": payload or {},
            "created_at": db.now_iso(),
        }],
        prefer="return=minimal",
    )


def list_events(session: dict, project_id: str, limit: int = 50) -> list[dict]:
    require_role(session, project_id, "viewer")
    response = _request_table(
        "project_events",
        "GET",
        params={
            "select": "id,actor_id,actor_email,kind,payload,created_at",
            "project_id": f"eq.{project_id}",
            "order": "created_at.desc",
            "limit": str(max(1, min(100, int(limit)))),
        },
    )
    return response.json() if response.content else []
