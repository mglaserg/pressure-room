from __future__ import annotations

from http.cookies import SimpleCookie

import httpx
import pytest
from cryptography.fernet import Fernet
from fastapi import HTTPException

from app import auth_store, supabase_store, workspace_ops


def configure_auth(monkeypatch):
    monkeypatch.setenv("PRESSURE_ROOM_AUTH_ENABLED", "true")
    monkeypatch.setenv("PRESSURE_ROOM_PUBLIC_URL", "https://pressure-room.example")
    monkeypatch.setenv("PRESSURE_ROOM_SESSION_KEY", Fernet.generate_key().decode())
    monkeypatch.setattr(supabase_store, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(supabase_store, "SUPABASE_SECRET_KEY", "sb_secret_test")


def test_magic_link_request_uses_supabase_otp_and_preserves_invite(monkeypatch):
    configure_auth(monkeypatch)
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return httpx.Response(200, json={})

    monkeypatch.setattr(httpx, "request", fake_request)
    auth_store.send_magic_link("Writer@Example.com", invite_token="invite-token")

    method, url, kwargs = calls[0]
    assert method == "POST"
    assert url.endswith("/auth/v1/otp")
    assert kwargs["json"] == {"email": "writer@example.com", "create_user": True}
    assert "invite=invite-token" in kwargs["params"]["redirect_to"]
    assert kwargs["headers"]["apikey"] == "sb_secret_test"


def test_magic_link_access_token_becomes_http_only_app_session(monkeypatch):
    configure_auth(monkeypatch)

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        assert url.endswith("/auth/v1/user")
        assert kwargs["headers"]["Authorization"] == "Bearer access-token"
        return httpx.Response(200, json={"id": "11111111-1111-1111-1111-111111111111", "email": "writer@example.com"})

    monkeypatch.setattr(httpx, "request", fake_request)
    response = auth_store.create_session_response("access-token")

    assert response.status_code == 204
    cookie = SimpleCookie()
    cookie.load(response.headers["set-cookie"])
    morsel = cookie[auth_store.AUTH_COOKIE]
    assert morsel["httponly"] is True
    assert morsel["secure"] is True
    decoded = auth_store._open(morsel.value)
    assert decoded["sub"] == "11111111-1111-1111-1111-111111111111"
    assert decoded["email"] == "writer@example.com"


def test_write_revision_check_enforces_editor_role_in_auth_mode(monkeypatch):
    monkeypatch.setenv("PRESSURE_ROOM_AUTH_ENABLED", "true")
    session = {"sub": "11111111-1111-1111-1111-111111111111", "email": "viewer@example.com"}
    token = workspace_ops._ACTIVE.set(session)
    try:
        def deny(*args, **kwargs):
            raise HTTPException(403, "This project requires editor access.")

        monkeypatch.setattr(supabase_store, "require_role", deny)

        class Request:
            headers = {"x-project-revision": "irrelevant"}

        with pytest.raises(HTTPException) as exc:
            workspace_ops.check_revision(Request(), "project-id")
        assert exc.value.status_code == 403
    finally:
        workspace_ops._ACTIVE.reset(token)


def test_invite_stores_only_hash_of_bearer_token(monkeypatch):
    monkeypatch.setenv("PRESSURE_ROOM_AUTH_ENABLED", "true")
    monkeypatch.setattr(supabase_store, "require_role", lambda *args, **kwargs: "owner")
    monkeypatch.setattr(supabase_store, "record_event", lambda *args, **kwargs: None)
    calls = []

    def fake_request_table(table, method, **kwargs):
        calls.append((table, method, kwargs))
        return httpx.Response(201, json=[])

    monkeypatch.setattr(supabase_store, "_request_table", fake_request_table)
    session = {"sub": "11111111-1111-1111-1111-111111111111", "email": "owner@example.com"}
    token = supabase_store.create_invite(session, "project-id", "editor@example.com", "editor")

    payload = calls[0][2]["json"][0]
    assert calls[0][0] == "project_invites"
    assert payload["email"] == "editor@example.com"
    assert payload["role"] == "editor"
    assert payload["token_hash"] != token
    assert token not in str(payload)


def test_member_upsert_never_downgrades_owner(monkeypatch):
    monkeypatch.setenv("PRESSURE_ROOM_AUTH_ENABLED", "true")
    configure_auth(monkeypatch)
    calls = []

    def fake_request_table(table, method, **kwargs):
        calls.append((table, method, kwargs))
        if method == "GET":
            return httpx.Response(200, json=[{"role": "owner", "created_at": "2026-09-29T12:00:00+00:00"}])
        return httpx.Response(201, json=[])

    monkeypatch.setattr(supabase_store, "_request_table", fake_request_table)
    session = {"sub": "11111111-1111-1111-1111-111111111111", "email": "owner@example.com"}
    supabase_store._upsert_member("project-id", session, "viewer")

    posted = [call for call in calls if call[1] == "POST"][0][2]["json"][0]
    assert posted["role"] == "owner"
    assert posted["created_at"] == "2026-09-29T12:00:00+00:00"


def test_trashed_project_is_hidden_even_from_existing_member(monkeypatch):
    configure_auth(monkeypatch)
    monkeypatch.setattr(supabase_store, "_project_meta", lambda project_id: {
        "project_id": project_id,
        "owner_id": "22222222-2222-2222-2222-222222222222",
        "trashed_at": "2026-09-29T16:00:00+00:00",
    })
    called = False

    def should_not_read_members(*args, **kwargs):
        nonlocal called
        called = True
        return httpx.Response(200, json=[{"role": "editor"}])

    monkeypatch.setattr(supabase_store, "_request_table", should_not_read_members)
    session = {"sub": "11111111-1111-1111-1111-111111111111", "email": "editor@example.com"}
    assert supabase_store.role_for(session, "project-id") is None
    assert called is False


def test_owner_can_soft_delete_and_restore_project(monkeypatch):
    configure_auth(monkeypatch)
    session = {"sub": "11111111-1111-1111-1111-111111111111", "email": "owner@example.com"}
    state = {"trashed": False}
    calls = []

    def fake_meta(project_id):
        return {
            "user_sub": session["sub"],
            "project_id": project_id,
            "owner_id": session["sub"],
            "trashed_at": "2026-09-29T16:00:00+00:00" if state["trashed"] else None,
        }

    def fake_request(method, **kwargs):
        calls.append(("projects", method, kwargs))
        if method == "PATCH":
            state["trashed"] = kwargs["json"].get("trashed_at") is not None
        return httpx.Response(200, json=[])

    monkeypatch.setattr(supabase_store, "_project_meta", fake_meta)
    monkeypatch.setattr(supabase_store, "_request", fake_request)
    monkeypatch.setattr(supabase_store, "_request_table", lambda table, method, **kwargs: calls.append((table, method, kwargs)) or httpx.Response(200, json=[]))
    monkeypatch.setattr(supabase_store, "record_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(supabase_store, "_upsert_member", lambda *args, **kwargs: None)

    supabase_store.trash_project(session, "project-id")
    assert state["trashed"] is True
    assert any(table == "project_presence" and method == "DELETE" for table, method, _ in calls)

    supabase_store.restore_project(session, "project-id")
    assert state["trashed"] is False


def test_permanent_delete_requires_trash_and_removes_metadata_before_story(monkeypatch):
    configure_auth(monkeypatch)
    session = {"sub": "11111111-1111-1111-1111-111111111111", "email": "owner@example.com"}
    monkeypatch.setattr(supabase_store, "_project_meta", lambda project_id: {
        "user_sub": session["sub"], "project_id": project_id, "owner_id": session["sub"],
        "trashed_at": "2026-09-29T16:00:00+00:00",
    })
    calls = []
    monkeypatch.setattr(supabase_store, "_request_table", lambda table, method, **kwargs: calls.append((table, method)) or httpx.Response(204))
    monkeypatch.setattr(supabase_store, "_request", lambda method, **kwargs: calls.append(("pressure_room_projects", method)) or httpx.Response(204))

    supabase_store.permanently_delete_project(session, "project-id")
    assert calls == [
        ("project_presence", "DELETE"),
        ("project_invites", "DELETE"),
        ("project_events", "DELETE"),
        ("project_members", "DELETE"),
        ("pressure_room_projects", "DELETE"),
    ]
