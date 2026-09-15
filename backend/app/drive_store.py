from __future__ import annotations

import hashlib
import re
import json
import os
import secrets
import threading
import time
from urllib.parse import urlencode, urlsplit

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from . import db
from .exporters import package_bytes, read_package, MAX_PACKAGE_BYTES

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
SESSION_KEY = os.getenv("PRESSURE_ROOM_SESSION_KEY", "").strip()
PUBLIC_URL = os.getenv("PRESSURE_ROOM_PUBLIC_URL", "").strip().rstrip("/")
GOOGLE_PICKER_API_KEY = os.getenv("GOOGLE_PICKER_API_KEY", "").strip()
GOOGLE_CLOUD_PROJECT_NUMBER = os.getenv("GOOGLE_CLOUD_PROJECT_NUMBER", "").strip()

SESSION_TTL = 60 * 60 * 24 * 90

COOKIE_NAME = "pressure_room_google"
STATE_COOKIE = "pressure_room_google_state"
FOLDER_NAME = "Pressure Room"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
SCOPES = f"openid email {DRIVE_SCOPE}"

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_V2_FILES_URL = "https://www.googleapis.com/drive/v2/files"
DRIVE_V2_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v2/files"

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
    url = urlsplit(PUBLIC_URL)
    if not url.hostname or url.username or url.password or url.query or url.fragment or url.path:
        return "PRESSURE_ROOM_PUBLIC_URL must be an origin without a path or credentials."
    if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost", "127.0.0.1", "::1"}):
        return "Google Drive requires HTTPS except on localhost."
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
        payload = json.loads(_fernet().decrypt(token.encode(), ttl=SESSION_TTL))
        return payload if isinstance(payload, dict) else None
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return None


def session_from_request(request: Request) -> dict | None:
    if not enabled() or configuration_error():
        return None
    session = _open(request.cookies.get(COOKIE_NAME, ""))
    if session:
        # Stable fingerprint supports revoking pre-upgrade cookies as well.
        sid = session.get('sid') or hashlib.sha256(request.cookies[COOKIE_NAME].encode()).hexdigest()
        db.bind_default_cache()
        if db.one('SELECT sid FROM revoked_sessions WHERE sid=? AND expires_at>?', [sid,time.time()]):
            return None
        session['sid'] = sid
    return session


def require_session(request: Request) -> dict:
    if not enabled():
        raise HTTPException(503, "Google Drive is not configured.")
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
        "picker_configured": bool(GOOGLE_PICKER_API_KEY and GOOGLE_CLOUD_PROJECT_NUMBER),
        "email": session.get("email") if session else None,
        "error": error,
    }


def connect_response() -> Response:
    if not enabled():
        raise HTTPException(503, "Google Drive is not configured.")
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
        try:
            error_payload = token_response.json()
        except Exception:
            error_payload = {}

        google_error = str(error_payload.get("error", "unknown_error"))
        google_description = str(
            error_payload.get("error_description", "No description returned by Google.")
        )
        raise HTTPException(
            502,
            f"Google OAuth token exchange failed: {google_error}: {google_description}",
        )
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
        "sid": secrets.token_urlsafe(32),
        "sub": sub,
        "email": email,
        "refresh_token": refresh,
        "access_token": access,
        "expires_at": time.time() + max(60, expires_in - 60),
    }
    response = RedirectResponse(f"{PUBLIC_URL}/", status_code=302)
    response.set_cookie(COOKIE_NAME, _seal(session), max_age=SESSION_TTL, httponly=True, secure=_secure_cookie(), samesite="lax", path="/")
    response.delete_cookie(STATE_COOKIE, path="/")
    return response


def disconnect_response(request: Request) -> Response:
    session = session_from_request(request)
    if session:
        db.bind_default_cache()
        db.execute('DELETE FROM revoked_sessions WHERE expires_at<?', [time.time()])
        db.execute('INSERT OR REPLACE INTO revoked_sessions(sid,expires_at) VALUES(?,?)', [session['sid'],time.time()+SESSION_TTL])
        ACCESS_CACHE.pop(session['sub'], None)
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



def picker_bootstrap(session: dict) -> dict:
    if not GOOGLE_PICKER_API_KEY or not GOOGLE_CLOUD_PROJECT_NUMBER:
        raise HTTPException(
            503,
            "Google Picker is not configured. Set GOOGLE_PICKER_API_KEY and GOOGLE_CLOUD_PROJECT_NUMBER.",
        )
    return {
        "access_token": access_token(session),
        "api_key": GOOGLE_PICKER_API_KEY,
        "app_id": GOOGLE_CLOUD_PROJECT_NUMBER,
    }


def file_metadata(session: dict, file_id: str) -> dict:
    return _request(
        session,
        "GET",
        f"{DRIVE_FILES_URL}/{validate_file_id(file_id)}",
        params={
            "fields": "id,name,mimeType,parents,modifiedTime,capabilities(canEdit)",
            "supportsAllDrives": "true",
        },
    ).json()


def validate_file_id(file_id: str) -> str:
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,200}', file_id or ''):
        raise HTTPException(400, 'Invalid Drive file identifier')
    return file_id


def file_revision(session: dict, file_id: str) -> str:
    # v2 explicitly exposes the file ETag. Never substitute modifiedTime/version.
    meta = _request(session, 'GET', f'{DRIVE_V2_FILES_URL}/{validate_file_id(file_id)}',
                    params={'fields':'etag', 'supportsAllDrives':'true'}).json()
    etag = meta.get('etag')
    if not isinstance(etag, str) or not etag or etag.startswith('W/'):
        raise HTTPException(409, 'Drive did not supply a safe write precondition. Download a recovery copy.')
    return etag


def bounded_download(session: dict, file_id: str, limit: int) -> bytes:
    url = f'{DRIVE_FILES_URL}/{validate_file_id(file_id)}'
    for attempt in range(2):
        with httpx.stream('GET', url, params={'alt':'media','supportsAllDrives':'true'},
                          headers={'Authorization':f'Bearer {access_token(session)}'}, timeout=HTTP_TIMEOUT) as response:
            if response.status_code == 401 and attempt == 0:
                ACCESS_CACHE.pop(_session_sub(session), None)
                ACCESS_CACHE[_session_sub(session)] = _refresh_access_token(session)
                continue
            if response.status_code >= 400:
                raise HTTPException(502, 'Could not download the Drive file.')
            chunks=[]; size=0
            for chunk in response.iter_bytes(65536):
                size += len(chunk)
                if size > limit:
                    raise HTTPException(413, 'Drive file exceeds the safe download limit.')
                chunks.append(chunk)
            return b''.join(chunks)
    raise HTTPException(401, 'Reconnect Google Drive.')


def download_text(session: dict, file_id: str) -> str:
    return bounded_download(session, file_id, 8*1024*1024).decode('utf-8-sig', errors='replace')


CONDITIONAL_WRITE_CHECKS: dict[str, float] = {}


def verify_conditional_writes(session: dict) -> None:
    """Probe a disposable app-owned file before trusting Drive write preconditions."""
    key=_session_sub(session)
    if time.monotonic()-CONDITIONAL_WRITE_CHECKS.get(key, -3601) < 3600:
        return
    probe=_request(session,'POST',DRIVE_FILES_URL,params={'fields':'id'},
        json={'name':'Pressure Room sync capability check','mimeType':'text/plain'}).json()['id']
    supported=False
    try:
        try:
            _request(session,'PUT',f'{DRIVE_V2_UPLOAD_URL}/{validate_file_id(probe)}',
                params={'uploadType':'media'}, headers={'Content-Type':'text/plain','If-Match':'"pressure-room-impossible-'+secrets.token_hex(32)+'"'},
                content=b'Conditional write probe; safe to delete.')
        except HTTPException as exc:
            if exc.status_code!=409:
                raise
            supported=True
    finally:
        # Cleanup failure also prevents proceeding to a real story overwrite.
        _request(session,'DELETE',f'{DRIVE_FILES_URL}/{validate_file_id(probe)}')
    if not supported:
        raise HTTPException(409,'Drive did not enforce conditional writes. Your story is kept here; download a backup.')
    CONDITIONAL_WRITE_CHECKS[key]=time.monotonic()


def upload_text(session: dict, file_id: str, text: str, etag: str) -> str:
    if not etag:
        raise HTTPException(409, 'Reload the linked Fountain file before saving.')
    verify_conditional_writes(session)
    response = _request(session, 'PUT', f'{DRIVE_V2_UPLOAD_URL}/{validate_file_id(file_id)}',
        params={'uploadType':'media','supportsAllDrives':'true','fields':'etag'},
        headers={'Content-Type':'text/plain; charset=utf-8','If-Match':etag}, content=text.encode())
    etag=response.json().get('etag')
    if not etag:
        etag=file_revision(session,file_id)
        remote=download_text(session,file_id)
        if remote!=text or file_revision(session,file_id)!=etag:
            raise HTTPException(409,'Fountain changed immediately after saving. Your story copy is preserved.')
    return etag

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
    if response.status_code == 404:
        raise HTTPException(404,"Drive file not found. Your local copy is preserved.")
    if response.status_code == 412:
        raise HTTPException(409, "Drive changed since you opened it. Your edits are preserved; choose a recovery copy or load Drive.")
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
    # Search all app-authorized Drive files so Fountain sidecars can live beside
    # their source screenplay instead of being forced into the Pressure Room folder.
    query = "appProperties has { key='pressure_room_kind' and value='project' } and trashed=false"
    return _list_files(session, query, "id,name,modifiedTime,appProperties,parents")

def _safe_filename(title: str) -> str:
    cleaned = "".join("_" if c in '<>:"/\\|?*' else c for c in title).strip().rstrip(".")
    return f"{cleaned or 'Untitled Story'}.pressureroom"


def _download_project(session: dict, file_id: str) -> dict:
    return read_package(bounded_download(session, file_id, MAX_PACKAGE_BYTES))


def _read_consistent(session, file_id):
    before = file_revision(session, file_id)
    payload = _download_project(session, file_id)
    after = file_revision(session, file_id)
    if before != after:
        raise HTTPException(409, 'Drive changed while it was being read. Try loading again.')
    return payload, after


def save_project(session: dict, project_id: str) -> dict:
    """Persist the exact upload intent; caller commits before draining it."""
    payload = db.project_payload(project_id, include_snapshots=True)
    operation_id = db.uid()
    payload['sync_revision'] = operation_id
    raw = package_bytes(payload)
    if len(raw) > MAX_PACKAGE_BYTES:
        raise HTTPException(413, 'Project backup exceeds 10 MiB. Export and trim snapshot history before syncing.')
    db.set_sync(project_id, operation_id=operation_id, payload_json=json.dumps(payload),
                stage='sidecar', status='pending', error='Waiting to sync with Drive.')
    return {'queued':True}


def _write_sidecar(session, project_id, job):
    payload = json.loads(job['payload_json'])
    raw = package_bytes(payload)
    file_id = job.get('file_id')
    if file_id:
        try:
            remote, current_etag = _read_consistent(session, file_id)
        except HTTPException as exc:
            if exc.status_code != 404 or job.get('etag'):
                raise
            remote = None
        if remote is None:
            return _create_sidecar(session, project_id, job, file_id)
        # A lost success response can be recognized without uploading twice.
        if remote == payload:
            return file_id, current_etag
        if not job.get('etag') or current_etag != job['etag']:
            raise HTTPException(409, 'This story changed in Drive. Keep your edits as a recovery copy or load the Drive version.')
        verify_conditional_writes(session)
        result = _request(session, 'PUT', f'{DRIVE_V2_UPLOAD_URL}/{file_id}',
            params={'uploadType':'media','fields':'etag','supportsAllDrives':'true'},
            headers={'Content-Type':'application/zip','If-Match':job['etag']}, content=raw)
        etag = result.json().get('etag')
        if not etag:
            # Do not accept an arbitrary later revision as the one we just wrote.
            check, etag = _read_consistent(session, file_id)
            if check != payload:
                raise HTTPException(409, 'Drive changed immediately after saving. Reload to review both versions.')
        return file_id, etag
    # A stable, pre-generated ID survives ambiguous create responses.
    file_id = _request(session,'GET',f'{DRIVE_FILES_URL}/generateIds',params={'count':1}).json()['ids'][0]
    db.set_sync(project_id, file_id=file_id)
    return _create_sidecar(session, project_id, job, file_id)


def _create_sidecar(session, project_id, job, file_id):
    payload=json.loads(job['payload_json'])
    raw=package_bytes(payload)
    source = db.get_project_source(project_id) or {}
    metadata = {'id':file_id,'name':source.get('sidecar_file_name') or _safe_filename(payload['project']['title']),
        'parents':[_folder_id(session)], 'appProperties':{'pressure_room_kind':'project','pressure_room_project_id':project_id}}
    boundary = 'pressure_room_' + secrets.token_hex(16)
    body = (f'--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n'.encode()
        + json.dumps(metadata).encode() + f'\r\n--{boundary}\r\nContent-Type: application/zip\r\n\r\n'.encode()
        + raw + f'\r\n--{boundary}--\r\n'.encode())
    _request(session,'POST',DRIVE_UPLOAD_URL,params={'uploadType':'multipart','fields':'id'},
        headers={'Content-Type':f'multipart/related; boundary={boundary}'},content=body)
    check, etag = _read_consistent(session, file_id)
    if check != payload:
        raise HTTPException(409, 'Drive changed after creation. Your local copy is preserved.')
    return file_id, etag


def drain_project(session, project_id):
    from . import fountain_link
    job = db.sync_job(project_id)
    if not job or job['stage'] == 'done':
        return db.sync_status(project_id)
    try:
        if job['stage'] in {'sidecar','final'}:
            file_id, etag = _write_sidecar(session, project_id, job)
            next_stage = 'done' if job['stage']=='final' else 'fountain'
            db.set_sync(project_id, file_id=file_id, etag=etag, stage=next_stage)
            job=db.sync_job(project_id)
        if job['stage']=='fountain':
            result = fountain_link.sync_to_fountain(session, project_id)
            if result and (result.get('updated') or
                    json.loads(job['payload_json']).get('project_source') != db.get_project_source(project_id)):
                payload=db.project_payload(project_id, include_snapshots=True)
                payload['sync_revision']=job['operation_id']+'-final'
                db.set_sync(project_id,payload_json=json.dumps(payload),stage='final')
                file_id,etag=_write_sidecar(session,project_id,db.sync_job(project_id))
                db.set_sync(project_id,file_id=file_id,etag=etag)
        db.set_sync(project_id,stage='done',status='synced',error='',payload_json=None)
    except (HTTPException, httpx.HTTPError, ValueError) as exc:
        conflict=isinstance(exc,HTTPException) and exc.status_code==409
        message=str(exc.detail) if isinstance(exc,HTTPException) else 'Drive is unavailable. Your pending save is retained on this server.'
        db.set_sync(project_id,status='conflict' if conflict else 'pending',error=message)
    return db.sync_status(project_id)


def sync_all_from_drive(session: dict) -> dict:
    sub = _bind_user_cache(session)
    with SYNC_LOCK:
<<<<<<< HEAD
        files=_project_files(session)
        # Never erase local or queued work just because a file disappeared remotely.
        pulled=0; pending=0
        for item in files:
            pid=(item.get('appProperties') or {}).get('pressure_room_project_id')
            if not pid:
                continue
            job=db.sync_job(pid)
            if job and job['stage']!='done':
                pending+=1
                continue
            if job and job.get('file_id') and job['file_id']!=item['id']:
                db.set_sync(pid,status='conflict',error='Two Drive files claim this story. Download copies and resolve the duplicate in Drive.')
                continue
            etag=file_revision(session,item['id'])
            if job and job.get('etag')==etag and db.one('SELECT id FROM projects WHERE id=?',[pid]):
                continue
            payload,etag=_read_consistent(session,item['id'])
            if payload['project']['id']!=pid:
                raise HTTPException(409,'Drive project identity does not match its file metadata.')
            with db.transaction():
                db.import_payload(payload,mode='replace')
                db.set_sync(pid,file_id=item['id'],etag=etag,stage='done',status='synced',error='')
            pulled+=1
        LAST_SYNC_AT[sub]=time.monotonic()
        return {'pulled':pulled,'pending':pending,'pushed':0}
=======
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
        with db.transaction():
            db.clear_projects()
            for payload in packages:
                db.import_payload(payload, mode="replace")
        LAST_SYNC_AT[sub] = time.monotonic()
        return {"pulled": len(packages), "pushed": 0}
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020


def ensure_local(session: dict, max_age_seconds: float = 15.0) -> None:
    sub=_bind_user_cache(session)
    last_sync=LAST_SYNC_AT.get(sub,0.0)
    if last_sync and time.monotonic()-last_sync<max_age_seconds:
        return
    try:
        sync_all_from_drive(session)
    except (HTTPException, httpx.HTTPError):
        if not db.get_projects():
            raise
        # Cached stories remain editable while Drive is unavailable. Uploads still
        # require the recorded ETag; failed refresh never grants overwrite rights.
        LAST_SYNC_AT[sub]=time.monotonic()


def resolve_project(session, project_id, action):
    job=db.sync_job(project_id)
    if not job:
        raise HTTPException(404,'No sync state for this story.')
    if action=='retry':
        return {'project_id':project_id,'sync':drain_project(session,project_id)}
    if action not in {'copy','load-drive'}:
        raise HTTPException(400,'Choose retry, copy or load-drive.')
    # Always make a separate local recovery story before replacing local work.
    with db.transaction():
        payload=db.project_payload(project_id,include_snapshots=True)
        payload['project']['title'] += ' — recovery'
        new_id=db.import_payload(payload,mode='copy')
    if action=='copy':
        save_project(session,new_id)
        drain_project(session,new_id)
        return {'project_id':new_id,'recovery_project_id':new_id,'sync':db.sync_status(new_id)}
    if not job.get('file_id'):
        raise HTTPException(409,'There is no remote version yet. Your recovery copy is available.')
    remote,etag=_read_consistent(session,job['file_id'])
    if remote['project']['id']!=project_id:
        raise HTTPException(409,'Drive project identity changed.')
    with db.transaction():
        db.import_payload(remote,mode='replace')
        db.set_sync(project_id,etag=etag,stage='done',status='synced',error='',payload_json=None)
        if job['stage']=='fountain' and db.get_project_source(project_id):
            from . import fountain_link
            fountain_link.reload_linked_fountain(session,project_id)
            save_project(session,project_id)
    drain_project(session,project_id)
    return {'project_id':project_id,'recovery_project_id':new_id,'sync':db.sync_status(project_id)}
