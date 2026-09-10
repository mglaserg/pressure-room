from __future__ import annotations

from typing import Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from . import db, drive_store
from .analysis import PRESSURE_MOVES, story_mri, writers_room_questions
from .exporters import package_bytes, read_package, project_markdown, fountain, pdf_bytes


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Pressure Room API", version="0.5.7", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Payload(BaseModel):
    data: dict[str, Any]


class NamePayload(BaseModel):
    name: str


class SnapshotPayload(BaseModel):
    label: str = "Snapshot"


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
    if not drive_store.enabled():
        return None
    session = drive_store.require_session(request)
    drive_store.ensure_local(session)
    return session


def _save(session: dict | None, project_id: str | None) -> None:
    if session and project_id:
        drive_store.save_project(session, project_id)


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "version": "0.5.7",
        "storage": drive_store.storage_mode(),
        "cache": db.database_backend(),
    }


@app.get("/api/ready")
def ready():
    try:
        db.ping()
    except Exception as exc:
        raise HTTPException(503, f"Local cache unavailable: {exc}")
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


@app.get("/api/google/disconnect")
def google_disconnect():
    return drive_store.disconnect_response()


@app.post("/api/google/sync")
def google_sync(request: Request):
    session = drive_store.require_session(request)
    return {"ok": True, **drive_store.sync_all_from_drive(session)}


@app.get("/api/projects")
def projects(request: Request):
    _prepare(request)
    return db.get_projects()


@app.post("/api/projects")
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
def get_workspace(project_id: str, request: Request):
    _prepare(request)
    try:
        return db.workspace(project_id)
    except KeyError:
        raise HTTPException(404, "Project not found")


@app.patch("/api/{table}/{object_id}")
def patch_object(table: str, object_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    if table not in PATCH_FIELDS:
        raise HTTPException(400, "Unsupported table")
    unknown = set(payload.data) - PATCH_FIELDS[table]
    if unknown:
        raise HTTPException(400, f"Unsupported fields: {', '.join(sorted(unknown))}")
    project_id = db.project_id_for_object(table, object_id)
    db.update(table, object_id, payload.data)
    _save(session, project_id)
    return {"ok": True}


@app.delete("/api/{table}/{object_id}")
def delete_object(table: str, object_id: str, request: Request):
    session = _prepare(request)
    allowed = {"characters", "episodes", "scenes", "bills", "causal_links", "branches"}
    if table not in allowed:
        raise HTTPException(400, "Unsupported table")
    project_id = db.project_id_for_object(table, object_id)
    db.delete(table, object_id)
    _save(session, project_id)
    return {"ok": True}


@app.post("/api/projects/{project_id}/characters")
def create_character(project_id: str, payload: Payload, request: Request):
    session = _prepare(request)
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
def create_episode(project_id: str, payload: Payload, request: Request):
    session = _prepare(request)
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
def create_scene(episode_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    episode = db.one("SELECT project_id FROM episodes WHERE id=?", [episode_id])
    if not episode:
        raise HTTPException(404, "Episode not found")
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
def create_link(episode_id: str, payload: Payload, request: Request):
    session = _prepare(request)
    episode = db.one("SELECT project_id FROM episodes WHERE id=?", [episode_id])
    if not episode:
        raise HTTPException(404, "Episode not found")
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
def create_bill(project_id: str, payload: Payload, request: Request):
    session = _prepare(request)
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
def clone_branch(project_id: str, branch_id: str, payload: NamePayload, request: Request):
    session = _prepare(request)
    try:
        new_id = db.clone_branch(project_id, branch_id, payload.name)
    except KeyError:
        raise HTTPException(404, "Branch not found")
    _save(session, project_id)
    return {"id": new_id}


@app.post("/api/projects/{project_id}/snapshots")
def create_snapshot(project_id: str, payload: SnapshotPayload, request: Request):
    session = _prepare(request)
    snapshot_id = db.create_snapshot(project_id, payload.label)
    _save(session, project_id)
    return {"id": snapshot_id}


@app.post("/api/snapshots/{snapshot_id}/restore")
def restore_snapshot(snapshot_id: str, request: Request):
    session = _prepare(request)
    snap = db.one("SELECT project_id FROM snapshots WHERE id=?", [snapshot_id])
    if not snap:
        raise HTTPException(404, "Snapshot not found")
    try:
        project_id = db.restore_snapshot(snapshot_id)
    except KeyError:
        raise HTTPException(404, "Snapshot not found")
    _save(session, project_id)
    return {"project_id": project_id}


@app.get("/api/episodes/{episode_id}/diagnostics")
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
def export(project_id: str, kind: str, request: Request):
    _prepare(request)
    try:
        payload = db.project_payload(project_id)
    except KeyError:
        raise HTTPException(404, "Project not found")
    title = payload["project"]["title"].replace("/", "-")
    if kind == "package":
        return Response(package_bytes(payload), media_type="application/zip", headers={"Content-Disposition": f'attachment; filename="{title}.pressureroom"'})
    if kind == "markdown":
        return Response(project_markdown(payload), media_type="text/markdown; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{title}-story-packet.md"'})
    if kind == "fountain":
        return Response(fountain(payload), media_type="text/plain; charset=utf-8", headers={"Content-Disposition": f'attachment; filename="{title}.fountain"'})
    if kind == "pdf":
        return Response(pdf_bytes(payload), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{title}-story-packet.pdf"'})
    raise HTTPException(400, "Unknown export kind")


@app.post("/api/import")
async def import_project(
    request: Request,
    file: UploadFile = File(...),
    mode: str = Query("copy", pattern="^(copy|replace)$"),
):
    session = _prepare(request)
    raw = await file.read()
    try:
        payload = read_package(raw)
        pid = db.import_payload(payload, mode=mode)
    except Exception as exc:
        raise HTTPException(400, f"Import failed: {exc}")
    _save(session, pid)
    return {"project_id": pid}
