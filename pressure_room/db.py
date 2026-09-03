from __future__ import annotations
import sqlite3
import uuid
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Iterable

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "pressure_room.db"

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def uid() -> str:
    return str(uuid.uuid4())

def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con

SCHEMA = """
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

CREATE INDEX IF NOT EXISTS idx_char_project ON characters(project_id);
CREATE INDEX IF NOT EXISTS idx_ep_project ON episodes(project_id);
CREATE INDEX IF NOT EXISTS idx_scene_episode ON scenes(episode_id);
CREATE INDEX IF NOT EXISTS idx_bill_project ON bills(project_id);
"""

def init_db():
    with connect() as con:
        con.executescript(SCHEMA)
        con.commit()
    ensure_demo()

def rows(sql: str, params: Iterable[Any] = ()) -> list[dict]:
    with connect() as con:
        return [dict(r) for r in con.execute(sql, tuple(params)).fetchall()]

def one(sql: str, params: Iterable[Any] = ()) -> dict | None:
    with connect() as con:
        r = con.execute(sql, tuple(params)).fetchone()
        return dict(r) if r else None

def execute(sql: str, params: Iterable[Any] = ()) -> None:
    with connect() as con:
        con.execute(sql, tuple(params))
        con.commit()

def insert(table: str, payload: dict) -> str:
    payload = dict(payload)
    payload.setdefault("id", uid())
    keys = list(payload)
    placeholders = ",".join("?" for _ in keys)
    with connect() as con:
        con.execute(
            f"INSERT INTO {table} ({','.join(keys)}) VALUES ({placeholders})",
            tuple(payload[k] for k in keys),
        )
        con.commit()
    return payload["id"]

def update(table: str, object_id: str, payload: dict) -> None:
    payload = dict(payload)
    if "updated_at" not in payload and table in {"projects","characters","episodes","scenes","bills"}:
        payload["updated_at"] = now_iso()
    sets = ",".join(f"{k}=?" for k in payload)
    vals = list(payload.values()) + [object_id]
    execute(f"UPDATE {table} SET {sets}, version=version+1 WHERE id=?", vals)

def delete(table: str, object_id: str) -> None:
    execute(f"DELETE FROM {table} WHERE id=?", [object_id])

def ensure_demo():
    if one("SELECT id FROM projects LIMIT 1"):
        return
    ts = now_iso()
    project_id = insert("projects", {
        "title": "The Last Favor",
        "premise": "A respected public defender secretly bends one rule to save a client, then must keep bending rules to protect the life built around that choice.",
        "theme": "Every shortcut writes a debt.",
        "created_at": ts, "updated_at": ts
    })
    branch_id = insert("branches", {
        "project_id": project_id, "name": "Main", "is_main": 1, "created_at": ts
    })
    char_id = insert("characters", {
        "project_id": project_id, "name": "Mara Vale", "role": "Protagonist",
        "want": "Win the impossible case and preserve her reputation.",
        "need": "Accept that control is not the same as integrity.",
        "core_belief": "If the system is unfair, bending it can be moral.",
        "moral_boundary": "I will never fabricate evidence.",
        "fear": "Becoming powerless in a system she understands too well.",
        "temptation": "Use superior knowledge of procedure to manufacture outcomes.",
        "moral_score": 2, "created_at": ts, "updated_at": ts
    })
    ep_id = insert("episodes", {
        "project_id": project_id, "branch_id": branch_id, "number": 1,
        "title": "A Clean Win", "logline": "Mara bends a procedural rule to save a client, then discovers the shortcut created a witness who can expose her.",
        "status": "Outline", "created_at": ts, "updated_at": ts
    })
    scene_ids = []
    scene_data = [
        (1, "INT. COURTHOUSE HALLWAY — MORNING", "Mara rehearses a closing argument while removing a coffee stain from her cuff.",
         "Get a key witness admitted.", "The judge has already ruled the witness out.", "Exploit a filing ambiguity.",
         "The hearing begins in twelve minutes.", "Backdate the internal receipt log.", "Certain she can still win clean.", "She wins the ruling, but only by crossing her own line.", "Mara closes the file before anyone can see her hand shaking.", 1),
        (2, "INT. RECORDS OFFICE — LATER", "A clerk slowly feeds the disputed filing into a scanner.",
         "Confirm the altered record is invisible.", "The clerk remembers the original timestamp.", "Act bored and conversational.",
         "The clerk asks why Mara is suddenly interested.", "Lie about an audit.", "Relieved the trick worked.", "Realizes a human witness now exists.", "The scanner beeps: duplicate timestamp.", 1),
        (3, "EXT. PARKING GARAGE — NIGHT", "Mara sits in her car without turning the engine on.",
         "Keep the clerk quiet without threatening him.", "He wants protection for an unrelated mistake.", "Offer legal help off the books.",
         "Helping him ties her to another irregularity.", "Agree to the favor.", "She thinks the damage can be contained.", "She has converted one lie into an obligation.", "Mara finally starts the engine.", 1),
    ]
    for sn, slug, opening, want, obstacle, tactic, pressure, choice, start, end, cut_on, moral_delta in scene_data:
        sid = insert("scenes", {
            "episode_id": ep_id, "scene_no": sn, "slugline": slug, "pov_character_id": char_id,
            "opening_behavior": opening, "scene_want": want, "obstacle": obstacle, "tactic": tactic,
            "pressure": pressure, "choice": choice, "start_state": start, "end_state": end,
            "cut_on": cut_on, "notes": "", "moral_delta": moral_delta,
            "created_at": ts, "updated_at": ts
        })
        scene_ids.append(sid)
    insert("causal_links", {"episode_id": ep_id, "from_scene_id": scene_ids[0], "relation": "BUT", "to_scene_id": scene_ids[1], "note": "The false filing creates a witness.", "created_at": ts})
    insert("causal_links", {"episode_id": ep_id, "from_scene_id": scene_ids[1], "relation": "THEREFORE", "to_scene_id": scene_ids[2], "note": "Mara must contain the clerk.", "created_at": ts})
    insert("bills", {
        "project_id": project_id, "episode_id": ep_id, "scene_id": scene_ids[0], "character_id": char_id,
        "title": "The altered timestamp", "external_cost": "The records clerk can expose the fabrication.",
        "moral_cost": "Mara has proven to herself that fabrication can work.",
        "status": "Escalating", "payoff_scene_id": None, "created_at": ts, "updated_at": ts
    })

def get_projects():
    return rows("SELECT * FROM projects ORDER BY updated_at DESC")

def get_characters(project_id: str):
    return rows("SELECT * FROM characters WHERE project_id=? ORDER BY name", [project_id])

def get_episodes(project_id: str):
    return rows("""
        SELECT e.*, b.name AS branch_name
        FROM episodes e JOIN branches b ON e.branch_id=b.id
        WHERE e.project_id=? ORDER BY e.number, e.created_at
    """, [project_id])

def get_scenes(episode_id: str):
    return rows("""
        SELECT s.*, c.name AS character_name
        FROM scenes s LEFT JOIN characters c ON s.pov_character_id=c.id
        WHERE s.episode_id=? ORDER BY s.scene_no, s.created_at
    """, [episode_id])

def get_links(episode_id: str):
    return rows("""
        SELECT l.*, a.scene_no AS from_no, a.slugline AS from_slug,
               b.scene_no AS to_no, b.slugline AS to_slug
        FROM causal_links l
        JOIN scenes a ON l.from_scene_id=a.id
        JOIN scenes b ON l.to_scene_id=b.id
        WHERE l.episode_id=? ORDER BY a.scene_no, b.scene_no
    """, [episode_id])

def get_bills(project_id: str):
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
