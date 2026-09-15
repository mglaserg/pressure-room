from __future__ import annotations

import os
import sqlite3
import zipfile
from urllib.parse import quote
from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel

from . import db, drive_store, fountain_link
from .request_limits import RequestLimitMiddleware
<<<<<<< HEAD
from . import workspace_ops
from .workspace_ops import workspace_request, check_revision
=======
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
from .analysis import PRESSURE_MOVES, story_mri, writers_room_questions
from .exporters import package_bytes, read_package, project_markdown, fountain, pdf_bytes, MAX_PACKAGE_BYTES


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


<<<<<<< HEAD
app = FastAPI(title="Pressure Room API", version="0.7.0", lifespan=lifespan)
=======
app = FastAPI(title="Pressure Room API", version="0.6.1", lifespan=lifespan)
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
app.add_middleware(RequestLimitMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    origin = request.headers.get("origin")
    allowed = {"http://localhost:3000", "http://127.0.0.1:3000", drive_store.PUBLIC_URL}
    allowed.update(v.strip() for v in os.getenv("PRESSURE_ROOM_ALLOWED_ORIGINS", "").split(",") if v.strip())
    if request.method not in {"GET", "HEAD", "OPTIONS"} and (
        request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin not in allowed)
    ):
        return JSONResponse({"detail": "Cross-origin write rejected"}, status_code=403)
    response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@app.exception_handler(ValueError)
@app.exception_handler(sqlite3.IntegrityError)
async def invalid_relationship(request, exc):
    return JSONResponse({"detail": "Invalid record value or relationship"}, status_code=400)


class Payload(BaseModel):
    data: dict[str, Any]


class NamePayload(BaseModel):
    name: str


class SnapshotPayload(BaseModel):
    label: str = "Snapshot"

class FountainOpenPayload(BaseModel):
    file_id: str


PATCH_FIELDS = {
    "projects": {"title", "premise", "theme"},
    "characters": {"name", "role", "want", "need", "core_belief", "moral_boundary", "fear", "temptation", "moral_score"},
    "episodes": {"number", "title", "logline", "status", "branch_id"},
    "scenes": {"scene_no", "slugline", "pov_character_id", "opening_behavior", "scene_want", "obstacle", "tactic", "pressure", "choice", "start_state", "end_state", "cut_on", "notes", "screenplay_text", "moral_delta"},
    "bills": {"episode_id", "scene_id", "character_id", "title", "external_cost", "moral_cost", "status", "payoff_scene_id"},
    "branches": {"name", "is_main"},
    "causal_links": {"from_scene_id", "relation", "to_scene_id", "note"},
}


def _prepare(request: Request) -> dict | None:
    if workspace_ops._ACTIVE.get() is not False:
        return workspace_ops._ACTIVE.get()
    if not drive_store.enabled():
        # Browser-local mode does not need the server database. Public deployments
        # must never fall back to sharing one anonymous SQLite workspace.
        if os.getenv("PRESSURE_ROOM_ALLOW_LOCAL_API", "").lower() != "true":
            raise HTTPException(403, "Server-local storage is disabled. Use browser storage or connect Google Drive.")
        db.bind_default_cache()
        return None
    session = drive_store.require_session(request)
    drive_store.ensure_local(session)
    return session


def _save(session: dict | None, project_id: str | None) -> None:
    if project_id:
        workspace_ops.changed(project_id)
    if session and project_id:
        drive_store.save_project(session, project_id)


@app.get("/api/health")
def health():
    return {
        "ok": True,
<<<<<<< HEAD
        "version": "0.7.0",
=======
        "version": "0.6.1",
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
        "storage": drive_store.storage_mode(),
        "cache": db.database_backend(),
    }


@app.get("/api/ready")
def ready():
    try:
        db.ping()
    except Exception as exc:
        raise HTTPException(503, "Local cache unavailable")
    error = drive_store.configuration_error()
    if error:
        raise HTTPException(503, error)
    return {"ok": True, "storage": drive_store.storage_mode()}


@app.get("/api/google/status")
def google_status(request: Request):
    return drive_store.status(request)


@app.get("/api/google/connect")
def google_connect():
    return drive_store.connect_response()


@app.get("/api/google/callback")
def google_callback(request: Request, code: str, state: str):
    return drive_store.callback_response(request, code, state)


@app.post("/api/google/disconnect")
<<<<<<< HEAD
def google_disconnect(request: Request):
    return drive_store.disconnect_response(request)
=======
def google_disconnect():
    return drive_store.disconnect_response()
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020


@app.post("/api/google/sync")
def google_sync(request: Request):
    session = drive_store.require_session(request)
    return {"ok": True, **drive_store.sync_all_from_drive(session)}




@app.get("/api/google/picker")
def google_picker(request: Request):
    session = drive_store.require_session(request)
    return drive_store.picker_bootstrap(session)


@app.post("/api/google/fountain/open")
@workspace_request
def google_fountain_open(payload: FountainOpenPayload, request: Request):
    session = _prepare(request)
    result = fountain_link.open_from_drive(session, payload.file_id)
    _save(session,result["project_id"])
    return result


@app.get("/api/projects")
@workspace_request
def projects(request: Request):
    _prepare(request)
    return db.get_projects()


@app.post("/api/projects")
@workspace_request
def create_project(payload: Payload, request: Request):
    session = _prepare(request)
    d = payload.data
    ts = db.now_iso()
    pid = db.insert(
        "projects",
        {
            "title": d.get("title", "Untitled Story").strip() or "Untitled Story",
            "premise": d.get("premise", ""),
            "theme": d.get("theme", ""),
            "created_at": ts,
            "updated_at": ts,
        },
    )
    db.insert("branches", {"project_id": pid, "name": "Main", "is_main": 1, "created_at": ts})
    _save(session, pid)
    return {"id": pid}


@app.get("/api/projects/{project_id}")
@workspace_request
def get_workspace(project_id: str, request: Request):
    _prepare(request)
    try:
        return db.workspace(project_id)
    except KeyError:
        raise HTTPException(404, "Project not found")


@app.patch("/api/{table}/{object_id}")
@workspace_request
def patch_object(table: str, object_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    if table not in PATCH_FIELDS:
        raise HTTPException(400, "Unsupported table")
    unknown = set(payload.data) - PATCH_FIELDS[table]
    if unknown:
        raise HTTPException(400, f"Unsupported fields: {', '.join(sorted(unknown))}")
    project_id = db.project_id_for_object(table, object_id)
    if not project_id:
        raise HTTPException(404, "Record not found")
<<<<<<< HEAD
    check_revision(request, project_id)
=======
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
    db.update(table, object_id, payload.data)
    _save(session, project_id)
    return {"ok": True}


@app.delete("/api/{table}/{object_id}")
@workspace_request
def delete_object(table: str, object_id: str, request: Request):
    session = _prepare(request)
    allowed = {"characters", "episodes", "scenes", "bills", "causal_links", "branches"}
    if table not in allowed:
        raise HTTPException(400, "Unsupported table")
    project_id = db.project_id_for_object(table, object_id)
    check_revision(request, project_id)
    db.delete(table, object_id)
    _save(session, project_id)
    return {"ok": True}


@app.post("/api/projects/{project_id}/characters")
@workspace_request
def create_character(project_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    check_revision(request, project_id)
    ts = db.now_iso()
    d = payload.data
    cid = db.insert(
        "characters",
        {
            "project_id": project_id,
            "name": d.get("name", "New Character"),
            "role": d.get("role", ""),
            "want": d.get("want", ""),
            "need": d.get("need", ""),
            "core_belief": d.get("core_belief", ""),
            "moral_boundary": d.get("moral_boundary", ""),
            "fear": d.get("fear", ""),
            "temptation": d.get("temptation", ""),
            "moral_score": int(d.get("moral_score", 0)),
            "created_at": ts,
            "updated_at": ts,
        },
    )
    _save(session, project_id)
    return {"id": cid}


@app.post("/api/projects/{project_id}/episodes")
@workspace_request
def create_episode(project_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    check_revision(request, project_id)
    d = payload.data
    ts = db.now_iso()
    main_branch = db.one("SELECT id FROM branches WHERE project_id=? AND is_main=1 LIMIT 1", [project_id])
    branch_id = d.get("branch_id") or (main_branch["id"] if main_branch else None)
    if not branch_id:
        raise HTTPException(400, "Project has no branch")
    eid = db.insert(
        "episodes",
        {
            "project_id": project_id,
            "branch_id": branch_id,
            "number": int(d.get("number", 1)),
            "title": d.get("title", "Untitled Episode"),
            "logline": d.get("logline", ""),
            "status": d.get("status", "Outline"),
            "created_at": ts,
            "updated_at": ts,
        },
    )
    _save(session, project_id)
    return {"id": eid}


@app.post("/api/episodes/{episode_id}/scenes")
@workspace_request
def create_scene(episode_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    episode = db.one("SELECT project_id FROM episodes WHERE id=?", [episode_id])
    if not episode:
        raise HTTPException(404, "Episode not found")
    check_revision(request, episode["project_id"])
    d = payload.data
    ts = db.now_iso()
    sid = db.insert(
        "scenes",
        {
            "episode_id": episode_id,
            "scene_no": int(d.get("scene_no", 1)),
            "slugline": d.get("slugline", ""),
            "pov_character_id": d.get("pov_character_id"),
            "opening_behavior": d.get("opening_behavior", ""),
            "scene_want": d.get("scene_want", ""),
            "obstacle": d.get("obstacle", ""),
            "tactic": d.get("tactic", ""),
            "pressure": d.get("pressure", ""),
            "choice": d.get("choice", ""),
            "start_state": d.get("start_state", ""),
            "end_state": d.get("end_state", ""),
            "cut_on": d.get("cut_on", ""),
            "notes": d.get("notes", ""),
            "screenplay_text": d.get("screenplay_text", ""),
            "moral_delta": int(d.get("moral_delta", 0)),
            "created_at": ts,
            "updated_at": ts,
        },
    )
    _save(session, episode["project_id"])
    return {"id": sid}


@app.post("/api/episodes/{episode_id}/links")
@workspace_request
def create_link(episode_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    episode = db.one("SELECT project_id FROM episodes WHERE id=?", [episode_id])
    if not episode:
        raise HTTPException(404, "Episode not found")
    check_revision(request, episode["project_id"])
    d = payload.data
    from_id = d.get("from_scene_id")
    to_id = d.get("to_scene_id")
    relation = str(d.get("relation", "")).upper()
    if not from_id or not to_id:
        raise HTTPException(400, "Choose both a source and destination scene")
    if from_id == to_id:
        raise HTTPException(400, "A scene cannot cause itself")
    if relation not in {"THEREFORE", "BUT"}:
        raise HTTPException(400, "Relationship must be THEREFORE or BUT")
    valid_scene_ids = {row["id"] for row in db.rows("SELECT id FROM scenes WHERE episode_id=?", [episode_id])}
    if from_id not in valid_scene_ids or to_id not in valid_scene_ids:
        raise HTTPException(400, "Both scenes must belong to the selected episode")
    duplicate = db.one(
        "SELECT id FROM causal_links WHERE episode_id=? AND from_scene_id=? AND relation=? AND to_scene_id=?",
        [episode_id, from_id, relation, to_id],
    )
    if duplicate:
        raise HTTPException(400, "That causal connection already exists")
    try:
        lid = db.insert(
            "causal_links",
            {
                "episode_id": episode_id,
                "from_scene_id": from_id,
                "relation": relation,
                "to_scene_id": to_id,
                "note": str(d.get("note", "")).strip(),
                "created_at": db.now_iso(),
            },
        )
    except Exception as exc:
        raise HTTPException(400, f"Could not create link: {exc}")
    _save(session, episode["project_id"])
    return {"id": lid}


@app.post("/api/projects/{project_id}/bills")
@workspace_request
def create_bill(project_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    check_revision(request, project_id)
    d = payload.data
    ts = db.now_iso()
    bid = db.insert(
        "bills",
        {
            "project_id": project_id,
            "episode_id": d.get("episode_id"),
            "scene_id": d.get("scene_id"),
            "character_id": d.get("character_id"),
            "title": d.get("title", "Untitled Bill"),
            "external_cost": d.get("external_cost", ""),
            "moral_cost": d.get("moral_cost", ""),
            "status": d.get("status", "Outstanding"),
            "payoff_scene_id": d.get("payoff_scene_id"),
            "created_at": ts,
            "updated_at": ts,
        },
    )
    _save(session, project_id)
    return {"id": bid}


@app.post("/api/projects/{project_id}/branches/{branch_id}/clone")
@workspace_request
def clone_branch(project_id: str, branch_id: str, payload: NamePayload, request: Request):
    session = _prepare(request)
    check_revision(request, project_id)
    try:
        new_id = db.clone_branch(project_id, branch_id, payload.name)
    except KeyError:
        raise HTTPException(404, "Branch not found")
    _save(session, project_id)
    return {"id": new_id}


@app.post("/api/projects/{project_id}/snapshots")
@workspace_request
def create_snapshot(project_id: str, payload: SnapshotPayload, request: Request):
    session = _prepare(request)
    check_revision(request, project_id)
    snapshot_id = db.create_snapshot(project_id, payload.label)
    _save(session, project_id)
    return {"id": snapshot_id}


@app.post("/api/snapshots/{snapshot_id}/restore")
@workspace_request
def restore_snapshot(snapshot_id: str, request: Request):
    session = _prepare(request)
    snap = db.one("SELECT project_id FROM snapshots WHERE id=?", [snapshot_id])
    if not snap:
        raise HTTPException(404, "Snapshot not found")
    check_revision(request, snap["project_id"])
    try:
        project_id = db.restore_snapshot(snapshot_id)
    except KeyError:
        raise HTTPException(404, "Snapshot not found")
    _save(session, project_id)
    return {"project_id": project_id}


@app.get("/api/episodes/{episode_id}/diagnostics")
@workspace_request
def diagnostics(episode_id: str, request: Request):
    _prepare(request)
    ep = db.one("SELECT * FROM episodes WHERE id=?", [episode_id])
    if not ep:
        raise HTTPException(404, "Episode not found")
    scenes = db.get_scenes(episode_id)
    bills = db.get_bills(ep["project_id"])
    chars = db.get_characters(ep["project_id"])
    protagonist = next((c for c in chars if c.get("role", "").lower() == "protagonist"), chars[0] if chars else None)
    return {
        "mri": story_mri(scenes, bills),
        "questions": writers_room_questions(protagonist, scenes, bills),
        "pressure_moves": [{"name": a, "description": b} for a, b in PRESSURE_MOVES],
    }


@app.get("/api/projects/{project_id}/export/{kind}")
@workspace_request
def export(project_id: str, kind: str, request: Request):
    _prepare(request)
    try:
        payload = db.project_payload(project_id, include_snapshots=(kind == "package"))
    except KeyError:
        raise HTTPException(404, "Project not found")
    title = "".join(c if c.isalnum() or c in " -_" else "_" for c in payload["project"]["title"])[:120] or "Story"
    def disposition(suffix):
        return {"Content-Disposition": f"attachment; filename=story{suffix}; filename*=UTF-8\'\'{quote(title + suffix, safe='')}"}
    if kind == "package":
        return Response(package_bytes(payload), media_type="application/zip", headers=disposition(".pressureroom"))
    if kind == "markdown":
        return Response(project_markdown(payload), media_type="text/markdown; charset=utf-8", headers=disposition("-story-packet.md"))
    if kind == "fountain":
        return Response(fountain(payload), media_type="text/plain; charset=utf-8", headers=disposition(".fountain"))
    if kind == "pdf":
        return Response(pdf_bytes(payload), media_type="application/pdf", headers=disposition("-story-packet.pdf"))
    raise HTTPException(400, "Unknown export kind")


@app.post("/api/import")
@workspace_request
def import_project(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Query("copy", pattern="^(copy|replace)$"),
):
    session = _prepare(request)
<<<<<<< HEAD
    raw = file.file.read(MAX_PACKAGE_BYTES + 1)
=======
    raw = await file.read(MAX_PACKAGE_BYTES + 1)
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
    if len(raw) > MAX_PACKAGE_BYTES:
        raise HTTPException(413, "Project package exceeds the 10 MiB limit")
    try:
        payload = read_package(raw)
        # A portable upload must not authorize writes to an embedded Drive file ID.
        payload.pop("project_source", None)
<<<<<<< HEAD
        if mode == "replace" and db.one("SELECT id FROM projects WHERE id=?", [payload["project"]["id"]]):
            check_revision(request, payload["project"]["id"])
=======
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
        pid = db.import_payload(payload, mode=mode)
    except (ValueError, KeyError, TypeError, sqlite3.Error, zipfile.BadZipFile, RuntimeError):
        raise HTTPException(400, "Invalid project package. No imported changes were saved.")
    _save(session, pid)
    return {"project_id": pid}


class ResolvePayload(BaseModel):
    action: str


@app.post('/api/projects/{project_id}/sync')
def resolve_sync(project_id: str, payload: ResolvePayload, request: Request):
    session=drive_store.require_session(request)
    with drive_store.SYNC_LOCK:
        drive_store._bind_user_cache(session)
        result=drive_store.resolve_project(session,project_id,payload.action)
        result['revision']=db.project_revision(result['project_id'])
        return result


@app.post('/api/projects/{project_id}/fountain-branch')
@workspace_request
def select_fountain_branch(project_id: str, payload: Payload, request: Request):
    session=_prepare(request)
    check_revision(request,project_id)
    source=db.get_project_source(project_id)
    branch_id=payload.data.get('branch_id')
    if not source or not db.one('SELECT id FROM branches WHERE id=? AND project_id=?',[branch_id,project_id]):
        raise HTTPException(400,'Choose a path belonging to this linked story.')
    db.upsert_project_source(project_id,branch_id=branch_id)
    _save(session,project_id)
    return {'ok':True}


@app.get('/api/projects/{project_id}/sync')
@workspace_request
def get_sync(project_id: str, request: Request):
    _prepare(request)
    return db.sync_status(project_id)
