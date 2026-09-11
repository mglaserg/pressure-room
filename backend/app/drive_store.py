from __future__ import annotations

import json
import os
import secrets
import threading
import time
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from . import db
from .exporters import package_bytes, read_package

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
SESSION_KEY = os.getenv("PRESSURE_ROOM_SESSION_KEY", "").strip()
PUBLIC_URL = os.getenv("PRESSURE_ROOM_PUBLIC_URL", "").strip().rstrip("/")

COOKIE_NAME = "pressure_room_google"
STATE_COOKIE = "pressure_room_google_state"
FOLDER_NAME = "Pressure Room"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
SCOPES = f"openid email {DRIVE_SCOPE}"

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"

HTTP_TIMEOUT = 25.0
SYNC_LOCK = threading.RLock()
LAST_SYNC_AT: dict[str, float] = {}
ACCESS_CACHE: dict[str, tuple[str, float]] = {}


def enabled() -> bool:
    return bool(GOOGLE_CLIENT_ID)


def _session_sub(session: dict) -> str:
    sub = str(session.get("sub", "")).strip()
    if not sub:
        raise HTTPException(401, "Google account identity is missing. Connect Google Drive again.")
    return sub


def _bind_user_cache(session: dict) -> str:
    sub = _session_sub(session)
    db.bind_user_cache(sub)
    return sub


def configuration_error() -> str | None:
    if not enabled():
        return None
    values = {
        "GOOGLE_CLIENT_ID": GOOGLE_CLIENT_ID,
        "GOOGLE_CLIENT_SECRET": GOOGLE_CLIENT_SECRET,
        "PRESSURE_ROOM_SESSION_KEY": SESSION_KEY,
        "PRESSURE_ROOM_PUBLIC_URL": PUBLIC_URL,
    }
    missing = [name for name, value in values.items() if not value]
    if missing:
        return "Missing Drive configuration: " + ", ".join(missing)
    try:
        Fernet(SESSION_KEY.encode())
    except Exception:
        return "PRESSURE_ROOM_SESSION_KEY is not a valid Fernet key."
    if not PUBLIC_URL.startswith(("http://", "https://")):
        return "PRESSURE_ROOM_PUBLIC_URL must be an absolute http(s) URL."
    return None


def storage_mode() -> str:
    return "google-drive" if enabled() else "local-sqlite"


def redirect_uri() -> str:
    return f"{PUBLIC_URL}/api/google/callback"


def _secure_cookie() -> bool:
    return PUBLIC_URL.startswith("https://")


def _fernet() -> Fernet:
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    return Fernet(SESSION_KEY.encode())


def _seal(payload: dict) -> str:
    return _fernet().encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()


def _open(token: str) -> dict | None:
    if not token:
        return None
    try:
        return json.loads(_fernet().decrypt(token.encode()))
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return None


def session_from_request(request: Request) -> dict | None:
    if not enabled() or configuration_error():
        return None
    return _open(request.cookies.get(COOKIE_NAME, ""))


def require_session(request: Request) -> dict:
    if not enabled():
        return {}
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    session = session_from_request(request)
    if not session:
        raise HTTPException(401, "Google Drive is not connected.")
    _session_sub(session)
    return session


def status(request: Request) -> dict:
    if not enabled():
        return {"required": False, "configured": False, "connected": False, "storage": "local-sqlite"}
    error = configuration_error()
    session = session_from_request(request) if not error else None
    return {
        "required": True,
        "configured": error is None,
        "connected": bool(session),
        "storage": "google-drive",
        "email": session.get("email") if session else None,
        "error": error,
    }


def connect_response() -> Response:
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    state = secrets.token_urlsafe(32)
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri(),
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
        "include_granted_scopes": "true",
        "state": state,
    }
    response = RedirectResponse(f"{AUTH_URL}?{urlencode(params)}", status_code=302)
    response.set_cookie(STATE_COOKIE, state, max_age=600, httponly=True, secure=_secure_cookie(), samesite="lax", path="/")
    return response


def callback_response(request: Request, code: str, state: str) -> Response:
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    expected = request.cookies.get(STATE_COOKIE, "")
    if not expected or not state or not secrets.compare_digest(expected, state):
        raise HTTPException(400, "Google OAuth state check failed. Start the Drive connection again.")

    token_response = httpx.post(
        TOKEN_URL,
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": redirect_uri(),
            "grant_type": "authorization_code",
        },
        timeout=HTTP_TIMEOUT,
    )
    if token_response.status_code >= 400:
        raise HTTPException(502, "Google did not accept the OAuth code.")
    token_data = token_response.json()
    access = token_data.get("access_token")
    refresh = token_data.get("refresh_token")
    if not access or not refresh:
        raise HTTPException(502, "Google did not return an offline refresh token. Revoke Pressure Room in Google and connect again.")

    user_response = httpx.get(USERINFO_URL, headers={"Authorization": f"Bearer {access}"}, timeout=HTTP_TIMEOUT)
    if user_response.status_code >= 400:
        raise HTTPException(502, "Could not read the connected Google account.")
    user = user_response.json()
    email = str(user.get("email", "")).lower()
    sub = str(user.get("sub", "")).strip()
    if not sub:
        raise HTTPException(502, "Google did not return a stable account identifier.")

    expires_in = int(token_data.get("expires_in", 3600))
    session = {
        "sub": sub,
        "email": email,
        "refresh_token": refresh,
        "access_token": access,
        "expires_at": time.time() + max(60, expires_in - 60),
    }
    response = RedirectResponse(f"{PUBLIC_URL}/", status_code=302)
    response.set_cookie(COOKIE_NAME, _seal(session), max_age=60 * 60 * 24 * 90, httponly=True, secure=_secure_cookie(), samesite="lax", path="/")
    response.delete_cookie(STATE_COOKIE, path="/")
    return response


def disconnect_response() -> Response:
    response = RedirectResponse(f"{PUBLIC_URL}/", status_code=302)
    response.delete_cookie(COOKIE_NAME, path="/")
    response.delete_cookie(STATE_COOKIE, path="/")
    return response


def _refresh_access_token(session: dict) -> tuple[str, float]:
    refresh = session.get("refresh_token")
    if not refresh:
        raise HTTPException(401, "Google Drive connection expired. Connect Google Drive again.")
    response = httpx.post(
        TOKEN_URL,
        data={
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "refresh_token": refresh,
            "grant_type": "refresh_token",
        },
        timeout=HTTP_TIMEOUT,
    )
    if response.status_code >= 400:
        raise HTTPException(401, "Google Drive authorization expired. Connect Google Drive again.")
    payload = response.json()
    token = payload.get("access_token")
    if not token:
        raise HTTPException(401, "Google Drive did not return a usable access token.")
    expires = time.time() + max(60, int(payload.get("expires_in", 3600)) - 60)
    return token, expires


def access_token(session: dict) -> str:
    key = _session_sub(session)
    cached = ACCESS_CACHE.get(key)
    if cached and cached[1] > time.time():
        return cached[0]
    token = session.get("access_token")
    expires = float(session.get("expires_at", 0))
    if token and expires > time.time():
        ACCESS_CACHE[key] = (token, expires)
        return token
    token, expires = _refresh_access_token(session)
    ACCESS_CACHE[key] = (token, expires)
    return token


def _request(session: dict, method: str, url: str, **kwargs) -> httpx.Response:
    token = access_token(session)
    headers = dict(kwargs.pop("headers", {}))
    headers["Authorization"] = f"Bearer {token}"
    response = httpx.request(method, url, headers=headers, timeout=HTTP_TIMEOUT, **kwargs)
    if response.status_code == 401:
        key = _session_sub(session)
        ACCESS_CACHE.pop(key, None)
        token, expires = _refresh_access_token(session)
        ACCESS_CACHE[key] = (token, expires)
        headers["Authorization"] = f"Bearer {token}"
        response = httpx.request(method, url, headers=headers, timeout=HTTP_TIMEOUT, **kwargs)
    if response.status_code >= 400:
        detail = ""
        try:
            detail = response.json().get("error", {}).get("message", "")
        except Exception:
            pass
        raise HTTPException(502, f"Google Drive request failed ({response.status_code}){': ' + detail if detail else ''}")
    return response


def _list_files(session: dict, query: str, fields: str) -> list[dict]:
    output: list[dict] = []
    page_token = None
    while True:
        params = {"q": query, "spaces": "drive", "pageSize": 100, "fields": f"nextPageToken,files({fields})"}
        if page_token:
            params["pageToken"] = page_token
        payload = _request(session, "GET", DRIVE_FILES_URL, params=params).json()
        output.extend(payload.get("files", []))
        page_token = payload.get("nextPageToken")
        if not page_token:
            return output


def _folder_id(session: dict) -> str:
    query = f"name='{FOLDER_NAME}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    folders = _list_files(session, query, "id,name")
    if folders:
        return folders[0]["id"]
    created = _request(
        session,
        "POST",
        DRIVE_FILES_URL,
        params={"fields": "id,name"},
        json={"name": FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
    ).json()
    return created["id"]


def _project_files(session: dict, folder_id: str | None = None) -> list[dict]:
    folder_id = folder_id or _folder_id(session)
    files = _list_files(session, f"'{folder_id}' in parents and trashed=false", "id,name,modifiedTime,appProperties")
    return [item for item in files if (item.get("appProperties") or {}).get("pressure_room_kind") == "project"]


def _safe_filename(title: str) -> str:
    cleaned = "".join("_" if c in '<>:"/\\|?*' else c for c in title).strip().rstrip(".")
    return f"{cleaned or 'Untitled Story'}.pressureroom"


def _download_project(session: dict, file_id: str) -> dict:
    raw = _request(session, "GET", f"{DRIVE_FILES_URL}/{file_id}", params={"alt": "media"}).content
    return read_package(raw)


def _upload_media(session: dict, file_id: str, raw: bytes) -> None:
    _request(
        session,
        "PATCH",
        f"{DRIVE_UPLOAD_URL}/{file_id}",
        params={"uploadType": "media"},
        headers={"Content-Type": "application/zip"},
        content=raw,
    )


def save_project(session: dict, project_id: str) -> dict:
    sub = _bind_user_cache(session)
    with SYNC_LOCK:
        payload = db.project_payload(project_id, include_snapshots=True)
        raw = package_bytes(payload)
        folder_id = _folder_id(session)
        files = _project_files(session, folder_id)
        current = next((item for item in files if (item.get("appProperties") or {}).get("pressure_room_project_id") == project_id), None)
        metadata = {
            "name": _safe_filename(payload["project"]["title"]),
            "appProperties": {
                "pressure_room_kind": "project",
                "pressure_room_project_id": project_id,
                "pressure_room_format_version": "2",
            },
        }
        if current:
            file_id = current["id"]
            _request(session, "PATCH", f"{DRIVE_FILES_URL}/{file_id}", params={"fields": "id,name,modifiedTime,appProperties"}, json=metadata)
        else:
            metadata["parents"] = [folder_id]
            created = _request(session, "POST", DRIVE_FILES_URL, params={"fields": "id,name,modifiedTime,appProperties"}, json=metadata).json()
            file_id = created["id"]
        _upload_media(session, file_id, raw)
        LAST_SYNC_AT[sub] = time.monotonic()
        return {"file_id": file_id, "name": metadata["name"]}


def sync_all_from_drive(session: dict) -> dict:
    sub = _bind_user_cache(session)
    with SYNC_LOCK:
        folder_id = _folder_id(session)
        project_files = _project_files(session, folder_id)
        if not project_files:
            local = db.get_projects()
            for project in local:
                save_project(session, project["id"])
            LAST_SYNC_AT[sub] = time.monotonic()
            return {"pulled": 0, "pushed": len(local)}

        packages = [_download_project(session, item["id"]) for item in project_files]
        if any(payload.get("format") != "pressure-room" for payload in packages):
            raise HTTPException(502, "A Pressure Room Drive file is not a valid project package.")
        db.clear_projects()
        for payload in packages:
            db.import_payload(payload, mode="replace")
        LAST_SYNC_AT[sub] = time.monotonic()
        return {"pulled": len(packages), "pushed": 0}


def ensure_local(session: dict, max_age_seconds: float = 15.0) -> None:
    sub = _bind_user_cache(session)
    last_sync = LAST_SYNC_AT.get(sub, 0.0)
    if last_sync and (time.monotonic() - last_sync) < max_age_seconds:
        return
    sync_all_from_drive(session)
