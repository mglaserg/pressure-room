from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("PRESSURE_ROOM_DB", ROOT / "data" / "pressure_room.db"))
_ACTIVE_DB_PATH: ContextVar[Path | None] = ContextVar(
    "pressure_room_active_db_path", default=None
)


def current_db_path() -> Path:
    return _ACTIVE_DB_PATH.get() or DB_PATH


def bind_default_cache() -> None:
    _ACTIVE_DB_PATH.set(None)


def bind_user_cache(user_sub: str) -> Path:
    user_sub = str(user_sub or "").strip()
    if not user_sub:
        raise ValueError("Google user sub is required for an isolated cache.")
    digest = hashlib.sha256(user_sub.encode("utf-8")).hexdigest()[:32]
    root = Path(
        os.getenv("PRESSURE_ROOM_USER_CACHE_DIR", str(DB_PATH.parent / "users"))
    )
    path = root / f"{digest}.db"
    _ACTIVE_DB_PATH.set(path)
    init_db(seed=False)
    return path


class SQLiteConnection(sqlite3.Connection):
    """SQLite connection that closes when a with-block exits."""

    def __exit__(self, exc_type, exc, tb):
        try:
            return super().__exit__(exc_type, exc, tb)
        finally:
            self.close()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def uid() -> str:
    return str(uuid.uuid4())


_TRANSACTION: ContextVar[sqlite3.Connection | None] = ContextVar("pressure_room_transaction", default=None)


@contextmanager
def connect():
    active = _TRANSACTION.get()
    if active is not None:
        yield active
        return
    path = current_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, factory=SQLiteConnection)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    with con:
        yield con


@contextmanager
def transaction():
    """Reuse one connection so a failed multi-row change rolls back entirely."""
    if _TRANSACTION.get() is not None:
        yield
        return
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        token = _TRANSACTION.set(con)
        try:
            yield
        finally:
            _TRANSACTION.reset(token)


SCHEMA = """
CREATE TABLE IF NOT EXISTS sync_jobs (
    project_id TEXT PRIMARY KEY,
    file_id TEXT,
    etag TEXT,
    operation_id TEXT,
    payload_json TEXT,
    stage TEXT NOT NULL DEFAULT 'done',
    status TEXT NOT NULL DEFAULT 'synced',
    error TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS revoked_sessions (
    sid TEXT PRIMARY KEY,
    expires_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    premise TEXT DEFAULT '',
    theme TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS branches (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    is_main INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    role TEXT DEFAULT '',
    want TEXT DEFAULT '',
    need TEXT DEFAULT '',
    core_belief TEXT DEFAULT '',
    moral_boundary TEXT DEFAULT '',
    fear TEXT DEFAULT '',
    temptation TEXT DEFAULT '',
    moral_score INTEGER NOT NULL DEFAULT 0 CHECK(moral_score BETWEEN 0 AND 10),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    branch_id TEXT NOT NULL REFERENCES branches(id) ON DELETE CASCADE,
    number INTEGER NOT NULL DEFAULT 1,
    title TEXT NOT NULL,
    logline TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Outline',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS scenes (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    scene_no INTEGER NOT NULL,
    slugline TEXT DEFAULT '',
    pov_character_id TEXT REFERENCES characters(id) ON DELETE SET NULL,
    opening_behavior TEXT DEFAULT '',
    scene_want TEXT DEFAULT '',
    obstacle TEXT DEFAULT '',
    tactic TEXT DEFAULT '',
    pressure TEXT DEFAULT '',
    choice TEXT DEFAULT '',
    start_state TEXT DEFAULT '',
    end_state TEXT DEFAULT '',
    cut_on TEXT DEFAULT '',
    notes TEXT DEFAULT '',
    screenplay_text TEXT DEFAULT '',
    moral_delta INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS causal_links (
    id TEXT PRIMARY KEY,
    episode_id TEXT NOT NULL REFERENCES episodes(id) ON DELETE CASCADE,
    from_scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    relation TEXT NOT NULL CHECK(relation IN ('THEREFORE','BUT')),
    to_scene_id TEXT NOT NULL REFERENCES scenes(id) ON DELETE CASCADE,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(episode_id, from_scene_id, relation, to_scene_id)
);
CREATE TABLE IF NOT EXISTS bills (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    episode_id TEXT REFERENCES episodes(id) ON DELETE SET NULL,
    scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    character_id TEXT REFERENCES characters(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    external_cost TEXT DEFAULT '',
    moral_cost TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'Outstanding' CHECK(status IN ('Outstanding','Escalating','Paid','Abandoned')),
    payoff_scene_id TEXT REFERENCES scenes(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS story_notes (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    object_type TEXT NOT NULL,
    object_id TEXT NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS project_sources (
    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    source_kind TEXT NOT NULL,
    drive_file_id TEXT NOT NULL UNIQUE,
    drive_file_name TEXT NOT NULL,
    drive_parent_id TEXT,
    sidecar_file_id TEXT,
    sidecar_file_name TEXT,
    fountain_preamble TEXT DEFAULT '',
    screenplay_hash TEXT DEFAULT '',
    source_modified_time TEXT DEFAULT '',
    linked_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_project_source_drive_file ON project_sources(drive_file_id);

CREATE INDEX IF NOT EXISTS idx_char_project ON characters(project_id);
CREATE INDEX IF NOT EXISTS idx_ep_project ON episodes(project_id);
CREATE INDEX IF NOT EXISTS idx_scene_episode ON scenes(episode_id);
CREATE INDEX IF NOT EXISTS idx_bill_project ON bills(project_id);
CREATE INDEX IF NOT EXISTS idx_snapshot_project ON snapshots(project_id);
"""


def database_backend() -> str:
    return "sqlite"


def ping() -> None:
    with connect() as con:
        con.execute("SELECT 1").fetchone()


def _has_column(con, table: str, column: str) -> bool:
    return any(r[1] == column for r in con.execute(f"PRAGMA table_info({table})"))


def init_db(seed: bool = True) -> None:
    with connect() as con:
        con.executescript(SCHEMA)
        for column in ('branch_id', 'source_etag'):
            if not _has_column(con, 'project_sources', column):
                con.execute(f'ALTER TABLE project_sources ADD COLUMN {column} TEXT')
        if not _has_column(con, "scenes", "screenplay_text"):
            con.execute("ALTER TABLE scenes ADD COLUMN screenplay_text TEXT DEFAULT ''")
    if seed:
        ensure_demo()


def rows(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with connect() as con:
        return [dict(r) for r in con.execute(sql, tuple(params)).fetchall()]


def one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    with connect() as con:
        row = con.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None


def execute(sql: str, params: Iterable[Any] = ()) -> None:
    with connect() as con:
        con.execute(sql, tuple(params))


def _validate_columns(table: str, data: dict) -> None:
    tables = {"projects", "branches", "characters", "episodes", "scenes", "causal_links", "bills", "story_notes", "snapshots", "project_sources"}
    if table not in tables:
        raise ValueError("Unsupported table")
    with connect() as con:
        allowed = {row[1] for row in con.execute(f"PRAGMA table_info({table})")}
    if set(data) - allowed:
        raise ValueError(f"Unsupported fields in {table}")


def _validate_relationships(table: str, data: dict) -> None:
    """Keep references within their story and causal links within their episode."""
    if table == "episodes":
        refs = [("branches", data.get("branch_id"))]
        project_id = data.get("project_id")
    elif table in {"scenes", "causal_links"}:
        ep = one("SELECT project_id FROM episodes WHERE id=?", [data.get("episode_id")])
        if not ep:
            raise ValueError("Episode not found")
        project_id = ep["project_id"]
        refs = [("characters", data.get("pov_character_id"))] if table == "scenes" else []
        if table == "causal_links":
            if data.get("from_scene_id") == data.get("to_scene_id"):
                raise ValueError("A scene cannot cause itself")
            for field in ("from_scene_id", "to_scene_id"):
                scene = one("SELECT episode_id FROM scenes WHERE id=?", [data.get(field)])
                if not scene or scene["episode_id"] != data["episode_id"]:
                    raise ValueError("Both scenes must belong to the selected episode")
    elif table == "bills":
        project_id = data.get("project_id")
        refs = [("episodes", data.get("episode_id")), ("characters", data.get("character_id")),
                ("scenes", data.get("scene_id")), ("scenes", data.get("payoff_scene_id"))]
    else:
        return
    for ref_table, ref_id in refs:
        if ref_id and project_id_for_object(ref_table, ref_id) != project_id:
            raise ValueError("Referenced record must belong to the same story")


def insert(table: str, payload: dict) -> str:
    data = dict(payload)
    if table != "project_sources":
        data.setdefault("id", uid())
    _validate_columns(table, data)
    _validate_relationships(table, data)
    keys = list(data)
    placeholders = ",".join("?" for _ in keys)
    with connect() as con:
        con.execute(
            f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
            tuple(data[k] for k in keys),
        )
    return data.get("id", data.get("project_id"))


def update(table: str, object_id: str, payload: dict) -> None:
    _validate_columns(table, payload)
    data = dict(payload)
<<<<<<< HEAD
    primary = "project_id" if table == "project_sources" else "id"
    existing = one(f"SELECT * FROM {table} WHERE {primary}=?", [object_id])
=======
    existing = one(f"SELECT * FROM {table} WHERE id=?", [object_id])
>>>>>>> 9830cc13d40f7eec2ea97e9dea308f7acb763020
    if not existing:
        raise KeyError(object_id)
    _validate_relationships(table, {**existing, **data})
    if not data:
        return
    if table in {"projects", "characters", "episodes", "scenes", "bills"}:
        data.setdefault("updated_at", now_iso())
        sets = ",".join(f"{k}=?" for k in data)
        vals = list(data.values()) + [object_id]
        execute(f"UPDATE {table} SET {sets}, version=version+1 WHERE id=?", vals)
    else:
        sets = ",".join(f"{k}=?" for k in data)
        vals = list(data.values()) + [object_id]
        execute(f"UPDATE {table} SET {sets} WHERE {primary}=?", vals)


def delete(table: str, object_id: str) -> None:
    _validate_columns(table, {})
    execute(f"DELETE FROM {table} WHERE id=?", [object_id])


def clear_projects() -> None:
    execute("DELETE FROM projects")


def project_id_for_object(table: str, object_id: str) -> str | None:
    if table == "projects":
        row = one("SELECT id AS project_id FROM projects WHERE id=?", [object_id])
    elif table in {"characters", "episodes", "bills", "branches", "snapshots"}:
        row = one(f"SELECT project_id FROM {table} WHERE id=?", [object_id])
    elif table == "scenes":
        row = one(
            "SELECT e.project_id FROM scenes s JOIN episodes e ON s.episode_id=e.id WHERE s.id=?",
            [object_id],
        )
    elif table == "causal_links":
        row = one(
            "SELECT e.project_id FROM causal_links l JOIN episodes e ON l.episode_id=e.id WHERE l.id=?",
            [object_id],
        )
    else:
        return None
    return row["project_id"] if row else None


def get_projects() -> list[dict]:
    return rows("SELECT * FROM projects ORDER BY updated_at DESC")


def get_characters(project_id: str) -> list[dict]:
    return rows("SELECT * FROM characters WHERE project_id=? ORDER BY name", [project_id])


def get_branches(project_id: str) -> list[dict]:
    return rows("SELECT * FROM branches WHERE project_id=? ORDER BY is_main DESC, created_at", [project_id])


def get_episodes(project_id: str) -> list[dict]:
    return rows("""
        SELECT e.*, b.name AS branch_name
        FROM episodes e JOIN branches b ON e.branch_id=b.id
        WHERE e.project_id=? ORDER BY b.is_main DESC, e.number, e.created_at
    """, [project_id])


def get_scenes(episode_id: str) -> list[dict]:
    return rows("""
        SELECT s.*, c.name AS character_name
        FROM scenes s LEFT JOIN characters c ON s.pov_character_id=c.id
        WHERE s.episode_id=? ORDER BY s.scene_no, s.created_at
    """, [episode_id])


def get_links(episode_id: str) -> list[dict]:
    return rows("""
        SELECT l.*, a.scene_no AS from_no, a.slugline AS from_slug,
               b.scene_no AS to_no, b.slugline AS to_slug
        FROM causal_links l
        JOIN scenes a ON l.from_scene_id=a.id
        JOIN scenes b ON l.to_scene_id=b.id
        WHERE l.episode_id=? ORDER BY a.scene_no, b.scene_no
    """, [episode_id])


def get_bills(project_id: str) -> list[dict]:
    return rows("""
        SELECT b.*, c.name AS character_name, e.number AS episode_no, s.scene_no AS scene_no
        FROM bills b
        LEFT JOIN characters c ON b.character_id=c.id
        LEFT JOIN episodes e ON b.episode_id=e.id
        LEFT JOIN scenes s ON b.scene_id=s.id
        WHERE b.project_id=?
        ORDER BY CASE b.status WHEN 'Escalating' THEN 0 WHEN 'Outstanding' THEN 1 WHEN 'Paid' THEN 2 ELSE 3 END,
                 b.created_at DESC
    """, [project_id])



def get_project_source(project_id: str) -> dict | None:
    return one("SELECT * FROM project_sources WHERE project_id=?", [project_id])


def get_project_source_by_drive_file(drive_file_id: str) -> dict | None:
    return one("SELECT * FROM project_sources WHERE drive_file_id=?", [drive_file_id])


def upsert_project_source(project_id: str, **fields) -> dict:
    allowed = {
        "source_kind", "branch_id", "source_etag",
        "drive_file_id",
        "drive_file_name",
        "drive_parent_id",
        "sidecar_file_id",
        "sidecar_file_name",
        "fountain_preamble",
        "screenplay_hash",
        "source_modified_time",
        "linked_at",
        "updated_at",
    }
    data = {k: v for k, v in fields.items() if k in allowed}
    existing = get_project_source(project_id)
    if existing:
        data.setdefault("updated_at", now_iso())
        update("project_sources", project_id, data)
        return get_project_source(project_id) or {}

    required = ("source_kind", "drive_file_id", "drive_file_name")
    missing = [name for name in required if not data.get(name)]
    if missing:
        raise ValueError("Missing project source fields: " + ", ".join(missing))
    data["project_id"] = project_id
    data.setdefault("linked_at", now_iso())
    data.setdefault("updated_at", now_iso())
    insert("project_sources", data)
    return get_project_source(project_id) or {}

def project_payload(project_id: str, include_snapshots: bool = False) -> dict:
    project = one("SELECT * FROM projects WHERE id=?", [project_id])
    if not project:
        raise KeyError(project_id)
    branches = get_branches(project_id)
    characters = get_characters(project_id)
    episodes = get_episodes(project_id)
    scenes: list[dict] = []
    links: list[dict] = []
    for episode in episodes:
        scenes.extend(get_scenes(episode["id"]))
        links.extend(get_links(episode["id"]))
    bills = get_bills(project_id)
    notes = rows("SELECT * FROM story_notes WHERE project_id=? ORDER BY created_at", [project_id])
    payload = {
        "format": "pressure-room",
        "format_version": 2 if include_snapshots else 1,
        "exported_at": now_iso(),
        "project": project,
        "branches": branches,
        "characters": characters,
        "episodes": episodes,
        "scenes": scenes,
        "causal_links": links,
        "bills": bills,
        "story_notes": notes,
        "project_source": get_project_source(project_id),
    }
    if include_snapshots:
        payload["snapshots"] = rows(
            "SELECT * FROM snapshots WHERE project_id=? ORDER BY created_at",
            [project_id],
        )
    return payload


def workspace(project_id: str) -> dict:
    payload = project_payload(project_id)
    payload["snapshots"] = rows(
        "SELECT id, project_id, label, created_at FROM snapshots WHERE project_id=? ORDER BY created_at DESC",
        [project_id],
    )
    payload["revision"] = project_revision(project_id)
    payload["sync"] = sync_status(project_id)
    return payload


def create_snapshot(project_id: str, label: str) -> str:
    payload = project_payload(project_id)
    return insert("snapshots", {
        "project_id": project_id,
        "label": label.strip() or "Snapshot",
        "payload_json": json.dumps(payload, ensure_ascii=False),
        "created_at": now_iso(),
    })


def restore_snapshot(snapshot_id: str) -> str:
    snap = one("SELECT * FROM snapshots WHERE id=?", [snapshot_id])
    if not snap:
        raise KeyError(snapshot_id)
    payload = json.loads(snap["payload_json"])
    if payload.get("project", {}).get("id") != snap["project_id"]:
        raise ValueError("Snapshot belongs to a different story")
    # History is story content, not authorization to write a linked Drive file.
    payload["project_source"] = get_project_source(snap["project_id"])
    return import_payload(payload, mode="replace")


def import_payload(payload: dict, mode: str = "copy") -> str:
    with transaction():
        return _import_payload(payload, mode)


def _import_payload(payload: dict, mode: str = "copy") -> str:
    if payload.get("format") != "pressure-room":
        raise ValueError("Not a Pressure Room project package")
    src = payload["project"]
    if mode not in {"copy", "replace"}:
        raise ValueError("mode must be copy or replace")
    retained_snapshots = []
    if mode == "replace":
        project_id = src["id"]
        if "snapshots" not in payload:
            retained_snapshots = rows("SELECT * FROM snapshots WHERE project_id=?", [project_id])
        if one("SELECT id FROM projects WHERE id=?", [project_id]):
            delete("projects", project_id)
        mapping = {project_id: project_id}
    else:
        project_id = uid()
        mapping = {src["id"]: project_id}

    def mapped(old: str | None) -> str | None:
        if old is None:
            return None
        if old not in mapping:
            mapping[old] = old if mode == "replace" else uid()
        return mapping[old]

    ts = now_iso()
    project = dict(src)
    project["id"] = project_id
    project["title"] = project["title"] if mode == "replace" else f"{project['title']} (imported)"
    project["updated_at"] = src.get("updated_at", ts) if mode == "replace" else ts
    insert("projects", project)

    for branch in payload.get("branches", []):
        data = {k: v for k, v in branch.items() if k != "id"}
        data["id"] = mapped(branch["id"])
        data["project_id"] = project_id
        insert("branches", data)
    for char in payload.get("characters", []):
        data = {k: v for k, v in char.items() if k not in {"id"}}
        data["id"] = mapped(char["id"])
        data["project_id"] = project_id
        insert("characters", data)
    for ep in payload.get("episodes", []):
        data = {k: v for k, v in ep.items() if k not in {"id", "branch_name"}}
        data["id"] = mapped(ep["id"])
        data["project_id"] = project_id
        data["branch_id"] = mapped(ep["branch_id"])
        insert("episodes", data)
    for scene in payload.get("scenes", []):
        data = {k: v for k, v in scene.items() if k not in {"id", "character_name"}}
        data["id"] = mapped(scene["id"])
        data["episode_id"] = mapped(scene["episode_id"])
        data["pov_character_id"] = mapped(scene.get("pov_character_id"))
        insert("scenes", data)
    for link in payload.get("causal_links", []):
        data = {k: v for k, v in link.items() if k not in {"id", "from_no", "from_slug", "to_no", "to_slug"}}
        data["id"] = mapped(link["id"])
        data["episode_id"] = mapped(link["episode_id"])
        data["from_scene_id"] = mapped(link["from_scene_id"])
        data["to_scene_id"] = mapped(link["to_scene_id"])
        insert("causal_links", data)
    for bill in payload.get("bills", []):
        data = {k: v for k, v in bill.items() if k not in {"id", "character_name", "episode_no", "scene_no"}}
        data["id"] = mapped(bill["id"])
        data["project_id"] = project_id
        data["episode_id"] = mapped(bill.get("episode_id"))
        data["scene_id"] = mapped(bill.get("scene_id"))
        data["character_id"] = mapped(bill.get("character_id"))
        data["payoff_scene_id"] = mapped(bill.get("payoff_scene_id"))
        insert("bills", data)
    for note in payload.get("story_notes", []):
        data = {k: v for k, v in note.items() if k != "id"}
        data["id"] = mapped(note["id"])
        data["project_id"] = project_id
        data["object_id"] = mapped(note.get("object_id")) or note.get("object_id", "")
        insert("story_notes", data)
    if mode == "replace":
        source = payload.get("project_source")
        if source:
            data = {k: v for k, v in source.items() if k != "project_id"}
            upsert_project_source(project_id, **data)

    if mode == "replace":
        for snap in payload.get("snapshots", retained_snapshots):
            data = {k: v for k, v in snap.items() if k != "id"}
            data["id"] = snap["id"]
            data["project_id"] = project_id
            insert("snapshots", data)
    if mode == "copy":
        for snap in payload.get("snapshots", []):
            historical = json.loads(snap["payload_json"]) if "payload_json" in snap else snap["payload"]
            historical = json.loads(json.dumps(historical))
            if historical.get("project", {}).get("id") != src["id"]:
                raise ValueError("Snapshot belongs to another story")
            historical.pop("snapshots", None)
            historical.pop("project_source", None)
            historical["project"]["id"] = project_id
            historical["project"]["title"] = project["title"]
            for table in ("branches","characters","episodes","scenes","causal_links","bills","story_notes"):
                for row in historical.get(table, []):
                    for key, value in list(row.items()):
                        if key == 'id' or key.endswith('_id'):
                            row[key] = mapped(value)
            insert('snapshots', {'project_id':project_id,'label':snap.get('label','Snapshot'),
                'created_at':snap.get('created_at',ts),'payload_json':json.dumps(historical)})
    return project_id


def clone_branch(project_id: str, branch_id: str, name: str) -> str:
    source = one("SELECT * FROM branches WHERE id=? AND project_id=?", [branch_id, project_id])
    if not source:
        raise KeyError(branch_id)
    new_branch = insert("branches", {
        "project_id": project_id, "name": name.strip() or f"{source['name']} copy",
        "is_main": 0, "created_at": now_iso(),
    })
    episode_map: dict[str, str] = {}
    scene_map: dict[str, str] = {}
    for ep in rows("SELECT * FROM episodes WHERE branch_id=? ORDER BY number", [branch_id]):
        data = {k: v for k, v in ep.items() if k != "id"}
        data.update({"project_id": project_id, "branch_id": new_branch, "created_at": now_iso(), "updated_at": now_iso(), "version": 1})
        new_ep = insert("episodes", data)
        episode_map[ep["id"]] = new_ep
        for sc in rows("SELECT * FROM scenes WHERE episode_id=? ORDER BY scene_no", [ep["id"]]):
            sd = {k: v for k, v in sc.items() if k != "id"}
            sd.update({"episode_id": new_ep, "created_at": now_iso(), "updated_at": now_iso(), "version": 1})
            new_sc = insert("scenes", sd)
            scene_map[sc["id"]] = new_sc
    for old_ep, new_ep in episode_map.items():
        for link in rows("SELECT * FROM causal_links WHERE episode_id=?", [old_ep]):
            insert("causal_links", {
                "episode_id": new_ep,
                "from_scene_id": scene_map[link["from_scene_id"]],
                "relation": link["relation"],
                "to_scene_id": scene_map[link["to_scene_id"]],
                "note": link.get("note", ""),
                "created_at": now_iso(),
            })
    for bill in rows("SELECT * FROM bills WHERE project_id=?", [project_id]):
        old_ep = bill.get("episode_id")
        if old_ep not in episode_map:
            continue
        bd = {k: v for k, v in bill.items() if k != "id"}
        bd["episode_id"] = episode_map.get(old_ep)
        bd["scene_id"] = scene_map.get(bill.get("scene_id"))
        bd["payoff_scene_id"] = scene_map.get(bill.get("payoff_scene_id"))
        bd["created_at"] = now_iso(); bd["updated_at"] = now_iso(); bd["version"] = 1
        insert("bills", bd)
    return new_branch


def ensure_demo() -> None:
    if one("SELECT id FROM projects LIMIT 1"):
        return
    ts = now_iso()
    project_id = insert("projects", {
        "title": "The Last Favor",
        "premise": "A respected public defender secretly bends one rule to save a client, then must keep bending rules to protect the life built around that choice.",
        "theme": "Every shortcut writes a debt.", "created_at": ts, "updated_at": ts,
    })
    branch_id = insert("branches", {"project_id": project_id, "name": "Main", "is_main": 1, "created_at": ts})
    char_id = insert("characters", {
        "project_id": project_id, "name": "Mara Vale", "role": "Protagonist",
        "want": "Win the impossible case and preserve her reputation.",
        "need": "Accept that control is not the same as integrity.",
        "core_belief": "If the system is unfair, bending it can be moral.",
        "moral_boundary": "I will never fabricate evidence.",
        "fear": "Becoming powerless in a system she understands too well.",
        "temptation": "Use superior knowledge of procedure to manufacture outcomes.",
        "moral_score": 2, "created_at": ts, "updated_at": ts,
    })
    ep_id = insert("episodes", {
        "project_id": project_id, "branch_id": branch_id, "number": 1, "title": "A Clean Win",
        "logline": "Mara bends a procedural rule to save a client, then discovers the shortcut created a witness who can expose her.",
        "status": "Outline", "created_at": ts, "updated_at": ts,
    })
    scenes = [
        (1, "INT. COURTHOUSE HALLWAY — MORNING", "Mara rehearses a closing argument while removing a coffee stain from her cuff.", "Get a key witness admitted.", "The judge has already ruled the witness out.", "Exploit a filing ambiguity.", "The hearing begins in twelve minutes.", "Backdate the internal receipt log.", "Certain she can still win clean.", "She wins the ruling, but only by crossing her own line.", "Mara closes the file before anyone can see her hand shaking.", 1, "MARA VALE stands alone beside a vending machine, rubbing at a coffee stain on her cuff.\n\nThe courthouse around her wakes up. She does not.\n\nShe checks the clock. Twelve minutes."),
        (2, "INT. RECORDS OFFICE — LATER", "A clerk slowly feeds the disputed filing into a scanner.", "Confirm the altered record is invisible.", "The clerk remembers the original timestamp.", "Act bored and conversational.", "The clerk asks why Mara is suddenly interested.", "Lie about an audit.", "Relieved the trick worked.", "Realizes a human witness now exists.", "The scanner beeps: duplicate timestamp.", 1, "The scanner hums.\n\nMara watches the clerk watch the page."),
        (3, "EXT. PARKING GARAGE — NIGHT", "Mara sits in her car without turning the engine on.", "Keep the clerk quiet without threatening him.", "He wants protection for an unrelated mistake.", "Offer legal help off the books.", "Helping him ties her to another irregularity.", "Agree to the favor.", "She thinks the damage can be contained.", "She has converted one lie into an obligation.", "Mara finally starts the engine.", 1, "Mara sits behind the wheel. Keys in her hand.\n\nShe could leave.\n\nShe makes the call instead."),
    ]
    scene_ids = []
    for sn, slug, opening, want, obstacle, tactic, pressure, choice, start, end, cut_on, delta, script in scenes:
        scene_ids.append(insert("scenes", {
            "episode_id": ep_id, "scene_no": sn, "slugline": slug, "pov_character_id": char_id,
            "opening_behavior": opening, "scene_want": want, "obstacle": obstacle, "tactic": tactic,
            "pressure": pressure, "choice": choice, "start_state": start, "end_state": end,
            "cut_on": cut_on, "notes": "", "screenplay_text": script, "moral_delta": delta,
            "created_at": ts, "updated_at": ts,
        }))
    insert("causal_links", {"episode_id": ep_id, "from_scene_id": scene_ids[0], "relation": "BUT", "to_scene_id": scene_ids[1], "note": "The false filing creates a witness.", "created_at": ts})
    insert("causal_links", {"episode_id": ep_id, "from_scene_id": scene_ids[1], "relation": "THEREFORE", "to_scene_id": scene_ids[2], "note": "Mara must contain the clerk.", "created_at": ts})
    insert("bills", {
        "project_id": project_id, "episode_id": ep_id, "scene_id": scene_ids[0], "character_id": char_id,
        "title": "The altered timestamp", "external_cost": "The records clerk can expose the fabrication.",
        "moral_cost": "Mara has proven to herself that fabrication can work.", "status": "Escalating",
        "payoff_scene_id": None, "created_at": ts, "updated_at": ts,
    })


def project_revision(project_id: str) -> str:
    payload = project_payload(project_id, include_snapshots=True)
    payload['project_source'] = {k:v for k,v in (payload.get('project_source') or {}).items() if k in {'branch_id','drive_file_id'}}
    for key in ('exported_at',):
        payload.pop(key, None)
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def sync_job(project_id: str) -> dict | None:
    return one('SELECT * FROM sync_jobs WHERE project_id=?', [project_id])


def sync_status(project_id: str) -> dict:
    job = sync_job(project_id)
    return {"status": job['status'] if job else 'local', "message": job['error'] if job else '',
            "updated_at": job['updated_at'] if job else None}


def set_sync(project_id: str, **fields) -> None:
    allowed = {'file_id','etag','operation_id','payload_json','stage','status','error'}
    if set(fields) - allowed:
        raise ValueError('Invalid sync state')
    with connect() as con:
        con.execute('INSERT OR IGNORE INTO sync_jobs(project_id,updated_at) VALUES(?,?)', [project_id,now_iso()])
        fields['updated_at'] = now_iso()
        con.execute(f"UPDATE sync_jobs SET {','.join(k+'=?' for k in fields)} WHERE project_id=?", [*fields.values(),project_id])
