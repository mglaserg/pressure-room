import httpx
import pytest

from app import db, supabase_store
from app.analysis import suspense_engine


@pytest.fixture
def story(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "supabase.db")
    db.bind_default_cache()
    db.init_db()
    yield db.get_projects()[0]["id"]
    db.bind_default_cache()


def test_suspense_engine_tracks_audience_debt_and_handoff():
    scenes = [
        {
            "id": "s1", "episode_id": "e1", "scene_no": 1, "slugline": "INT. OFFICE - DAY",
            "audience_knows": "The recorder is running.",
            "audience_waits_for": "Will Mara notice it?",
            "withheld_information": "Who planted it?",
        },
        {"id": "s2", "episode_id": "e1", "scene_no": 2, "slugline": "EXT. GARAGE - NIGHT"},
    ]
    bills = [{
        "title": "The altered timestamp", "episode_id": "e1", "scene_id": "s1",
        "payoff_scene_id": "s2", "status": "Escalating",
    }]
    links = [{"from_scene_id": "s1", "to_scene_id": "s2", "relation": "BUT"}]

    rows = suspense_engine(scenes, bills, links)

    assert rows[0]["active_hooks"] == ["waiting", "withheld", "knowledge gap", "unpaid bill", "causal handoff"]
    assert rows[0]["open_bills"] == ["The altered timestamp"]
    assert rows[0]["handoff"] == ["BUT → S2"]
    assert rows[1]["paying_off"] == ["The altered timestamp"]


def test_supabase_compare_and_swap_uses_existing_story_revision(story, monkeypatch):
    monkeypatch.setattr(supabase_store, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(supabase_store, "SUPABASE_SERVICE_ROLE_KEY", "service-secret")
    revision = db.project_revision(story)
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return httpx.Response(200, json=[{"project_id": story, "revision": revision}])

    monkeypatch.setattr(httpx, "request", fake_request)
    result = supabase_store.save_project({"sub": "google-user"}, story, expected_revision=revision)

    assert result["stored"] is True
    method, _, kwargs = calls[0]
    assert method == "PATCH"
    assert kwargs["params"]["revision"] == f"eq.{revision}"
    assert kwargs["json"]["payload"]["project"]["id"] == story
    assert kwargs["headers"]["Authorization"] == "Bearer service-secret"


def test_supabase_stale_compare_and_swap_returns_conflict(story, monkeypatch):
    monkeypatch.setattr(supabase_store, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(supabase_store, "SUPABASE_SERVICE_ROLE_KEY", "service-secret")

    def fake_request(*args, **kwargs):
        return httpx.Response(200, json=[])

    monkeypatch.setattr(httpx, "request", fake_request)
    try:
        supabase_store.save_project({"sub": "google-user"}, story, expected_revision="older")
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 409
    else:
        raise AssertionError("stale durable write should conflict")


def test_supabase_hydrate_restores_story_and_drive_state(story, monkeypatch):
    monkeypatch.setattr(supabase_store, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(supabase_store, "SUPABASE_SERVICE_ROLE_KEY", "service-secret")
    payload = db.project_payload(story, include_snapshots=True)
    payload["project"]["title"] = "Durable title"

    with pytest.raises(RuntimeError):
        with db.transaction():
            db.import_payload(payload, mode="replace")
            durable_revision = db.project_revision(story)
            raise RuntimeError("rollback")

    record = {
        "project_id": story,
        "payload": payload,
        "revision": durable_revision,
        "sync_state": {
            "file_id": "drive-file",
            "etag": '"etag-1"',
            "operation_id": "op",
            "payload_json": None,
            "stage": "done",
            "status": "synced",
            "error": "",
        },
        "updated_at": "2026-09-28T12:00:00+00:00",
    }

    def fake_request(method, url, **kwargs):
        assert method == "GET"
        return httpx.Response(200, json=[record])

    monkeypatch.setattr(httpx, "request", fake_request)
    result = supabase_store.hydrate_user({"sub": "google-user"})

    assert result == {"pulled": 1, "remote": 1}
    assert db.project_payload(story)["project"]["title"] == "Durable title"
    assert db.sync_job(story)["file_id"] == "drive-file"


def test_durable_write_failure_rolls_back_local_mutation(story, monkeypatch):
    from fastapi import HTTPException
    from app import main

    before = {item['id'] for item in db.get_projects()}
    monkeypatch.setattr(main, '_prepare', lambda request: {'sub': 'google-user'})
    monkeypatch.setattr(supabase_store, 'enabled', lambda: True)
    monkeypatch.setattr(
        supabase_store,
        'save_project',
        lambda *args, **kwargs: (_ for _ in ()).throw(HTTPException(503, 'durable store down')),
    )

    with pytest.raises(HTTPException) as exc:
        main.create_project(payload=main.Payload(data={'title': 'Must roll back'}), request=object())

    assert exc.value.status_code == 503
    assert {item['id'] for item in db.get_projects()} == before
