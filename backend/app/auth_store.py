from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, Response

from . import supabase_store

AUTH_COOKIE = "pressure_room_auth"
AUTH_TTL_SECONDS = 60 * 60 * 24 * 14
HTTP_TIMEOUT = 15.0
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def enabled() -> bool:
    return _flag("PRESSURE_ROOM_AUTH_ENABLED")


def configuration_error() -> str | None:
    if not enabled():
        return None
    if not supabase_store.enabled():
        return "Magic-link auth requires SUPABASE_URL and SUPABASE_SECRET_KEY."
    public_url = os.getenv("PRESSURE_ROOM_PUBLIC_URL", "").strip().rstrip("/")
    session_key = os.getenv("PRESSURE_ROOM_SESSION_KEY", "").strip()
    if not public_url:
        return "Magic-link auth requires PRESSURE_ROOM_PUBLIC_URL."
    if not public_url.startswith("https://") and not public_url.startswith("http://localhost") and not public_url.startswith("http://127.0.0.1"):
        return "PRESSURE_ROOM_PUBLIC_URL must use HTTPS outside localhost."
    try:
        Fernet(session_key.encode())
    except Exception:
        return "Magic-link auth requires a valid PRESSURE_ROOM_SESSION_KEY Fernet key."
    return None


def _fernet() -> Fernet:
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    return Fernet(os.environ["PRESSURE_ROOM_SESSION_KEY"].encode())


def _secure_cookie() -> bool:
    return os.getenv("PRESSURE_ROOM_PUBLIC_URL", "").strip().startswith("https://")


def _seal(payload: dict) -> str:
    return _fernet().encrypt(json.dumps(payload, separators=(",", ":")).encode()).decode()


def _open(token: str) -> dict | None:
    if not token:
        return None
    try:
        payload = json.loads(_fernet().decrypt(token.encode(), ttl=AUTH_TTL_SECONDS))
        return payload if isinstance(payload, dict) else None
    except (InvalidToken, ValueError, TypeError, json.JSONDecodeError):
        return None


def session_from_request(request: Request) -> dict | None:
    if not enabled() or configuration_error():
        return None
    session = _open(request.cookies.get(AUTH_COOKIE, ""))
    if not session:
        return None
    sub = str(session.get("sub") or "").strip()
    email = str(session.get("email") or "").strip().lower()
    if not sub or not email:
        return None
    return {**session, "sub": sub, "email": email}


def require_session(request: Request) -> dict:
    if not enabled():
        raise HTTPException(503, "Pressure Room magic-link auth is not enabled.")
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    session = session_from_request(request)
    if not session:
        raise HTTPException(401, "Sign in to open this cloud workspace.")
    return session


def status(request: Request) -> dict:
    error = configuration_error()
    session = session_from_request(request) if not error else None
    return {
        "enabled": enabled(),
        "configured": enabled() and error is None,
        "authenticated": bool(session),
        "user_id": session.get("sub") if session else None,
        "email": session.get("email") if session else None,
        "error": error,
    }


def _auth_request(method: str, path: str, *, params: dict | None = None, json_body: dict | None = None, bearer: str | None = None) -> httpx.Response:
    error = configuration_error()
    if error:
        raise HTTPException(503, error)
    headers = {
        "apikey": supabase_store.SUPABASE_SECRET_KEY,
        "Content-Type": "application/json",
    }
    if bearer:
        headers["Authorization"] = f"Bearer {bearer}"
    try:
        response = httpx.request(
            method,
            f"{supabase_store.SUPABASE_URL}/auth/v1/{path.lstrip('/')}",
            params=params,
            json=json_body,
            headers=headers,
            timeout=HTTP_TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Supabase Auth is temporarily unavailable.") from exc
    if response.status_code >= 400:
        detail = ""
        try:
            payload = response.json()
            detail = str(payload.get("msg") or payload.get("message") or payload.get("error_description") or payload.get("error") or "")
        except Exception:
            pass
        suffix = f" ({detail[:180]})" if detail else ""
        code = 429 if response.status_code == 429 else 400
        raise HTTPException(code, f"Supabase Auth rejected the request{suffix}")
    return response


def send_magic_link(email: str, *, invite_token: str | None = None) -> None:
    email = str(email or "").strip().lower()
    if len(email) > 320 or not _EMAIL_RE.fullmatch(email):
        raise HTTPException(400, "Enter a valid email address.")
    public_url = os.environ["PRESSURE_ROOM_PUBLIC_URL"].strip().rstrip("/")
    query = {"auth_callback": "1"}
    if invite_token:
        query["invite"] = invite_token
    redirect_to = f"{public_url}/?{urlencode(query)}"
    _auth_request(
        "POST",
        "otp",
        params={"redirect_to": redirect_to},
        json_body={"email": email, "create_user": True},
    )


def create_session_response(access_token: str) -> Response:
    if not enabled():
        raise HTTPException(503, "Pressure Room magic-link auth is not enabled.")
    token = str(access_token or "").strip()
    if not token:
        raise HTTPException(400, "Magic-link session token is missing.")
    response = _auth_request("GET", "user", bearer=token)
    user = response.json()
    sub = str(user.get("id") or "").strip()
    email = str(user.get("email") or "").strip().lower()
    if not sub or not email:
        raise HTTPException(502, "Supabase did not return a usable user identity.")
    session = {
        "sub": sub,
        "email": email,
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    out = Response(status_code=204)
    out.set_cookie(
        AUTH_COOKIE,
        _seal(session),
        max_age=AUTH_TTL_SECONDS,
        httponly=True,
        secure=_secure_cookie(),
        samesite="lax",
        path="/",
    )
    return out


def logout_response() -> Response:
    response = Response(status_code=204)
    response.delete_cookie(AUTH_COOKIE, path="/")
    return response
