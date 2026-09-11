
from __future__ import annotations

import hashlib
import re
from pathlib import Path

from fastapi import HTTPException

from . import db, drive_store

SCENE_RE = re.compile(
    r"^(?:\.)?(?:INT\.?|EXT\.?|EST\.?|INT/EXT\.?|INT\./EXT\.?|EXT/INT\.?|EXT\./INT\.?|I/E\.?)\b",
    re.IGNORECASE,
)


def _title_from_preamble(preamble: str, fallback: str) -> str:
    for line in preamble.splitlines():
        if line.lower().startswith("title:"):
            title = line.split(":", 1)[1].strip()
            if title:
                return title
    return fallback


def _is_scene_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if SCENE_RE.match(stripped):
        return True
    # Fountain supports forced scene headings with a leading period.
    return stripped.startswith(".") and not stripped.startswith("..") and len(stripped) > 1


def parse_fountain(text: str, filename: str) -> dict:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")
    scene_indexes = [i for i, line in enumerate(lines) if _is_scene_heading(line)]

    fallback_title = Path(filename).stem or "Untitled Story"
    if not scene_indexes:
        return {
            "title": _title_from_preamble(text, fallback_title),
            "preamble": "",
            "scenes": [{"slugline": "", "screenplay_text": text.strip()}],
        }

    first = scene_indexes[0]
    preamble = "\n".join(lines[:first]).rstrip()
    scenes: list[dict] = []

    for pos, start in enumerate(scene_indexes):
        stop = scene_indexes[pos + 1] if pos + 1 < len(scene_indexes) else len(lines)
        heading = lines[start].strip()
        if heading.startswith("."):
            heading = heading[1:].strip()
        body = "\n".join(lines[start + 1 : stop]).strip("\n")
        scenes.append({"slugline": heading, "screenplay_text": body.rstrip()})

    return {
        "title": _title_from_preamble(preamble, fallback_title),
        "preamble": preamble,
        "scenes": scenes,
    }


def _screenplay_material(project_id: str) -> str:
    payload = db.project_payload(project_id)
    chunks: list[str] = []
    for episode in payload.get("episodes", []):
        episode_scenes = [
            scene
            for scene in payload.get("scenes", [])
            if scene["episode_id"] == episode["id"]
        ]
        episode_scenes.sort(key=lambda row: (int(row.get("scene_no", 0)), row.get("created_at", "")))
        for scene in episode_scenes:
            chunks.append((scene.get("slugline") or "").strip())
            chunks.append((scene.get("screenplay_text") or "").rstrip())
    return "\n\x1e\n".join(chunks)


def screenplay_hash(project_id: str) -> str:
    return hashlib.sha256(_screenplay_material(project_id).encode("utf-8")).hexdigest()


def _render_linked_fountain(project_id: str, preamble: str) -> str:
    payload = db.project_payload(project_id)
    out: list[str] = []
    preamble = (preamble or "").rstrip()

    if preamble:
        out.append(preamble)
        out.extend(["", ""])
    else:
        out.extend(
            [
                f"Title: {payload['project']['title']}",
                "Credit: Written in Pressure Room",
                "",
                "",
            ]
        )

    episodes = payload.get("episodes", [])
    multiple_episodes = len(episodes) > 1

    for episode in episodes:
        if multiple_episodes:
            out.extend([f"# E{episode['number']} — {episode['title']}", ""])
        episode_scenes = [
            scene
            for scene in payload.get("scenes", [])
            if scene["episode_id"] == episode["id"]
        ]
        episode_scenes.sort(key=lambda row: (int(row.get("scene_no", 0)), row.get("created_at", "")))
        for scene in episode_scenes:
            slugline = (scene.get("slugline") or "").strip()
            body = (scene.get("screenplay_text") or "").rstrip()
            if slugline:
                out.extend([slugline, ""])
            if body:
                out.extend([body, ""])

    return "\n".join(out).rstrip() + "\n"


def open_from_drive(session: dict, file_id: str) -> dict:
    file_id = str(file_id or "").strip()
    if not file_id:
        raise HTTPException(400, "Choose a Fountain file first.")

    existing = db.get_project_source_by_drive_file(file_id)
    if existing:
        return {
            "project_id": existing["project_id"],
            "linked": True,
            "already_linked": True,
            "file_name": existing["drive_file_name"],
        }

    meta = drive_store.file_metadata(session, file_id)
    name = str(meta.get("name", "")).strip()
    if not name.lower().endswith(".fountain"):
        raise HTTPException(400, "Choose a .fountain file from Google Drive.")

    text = drive_store.download_text(session, file_id)
    parsed = parse_fountain(text, name)
    ts = db.now_iso()

    project_id = db.insert(
        "projects",
        {
            "title": parsed["title"].strip() or Path(name).stem or "Untitled Story",
            "premise": "",
            "theme": "",
            "created_at": ts,
            "updated_at": ts,
        },
    )
    branch_id = db.insert(
        "branches",
        {
            "project_id": project_id,
            "name": "Main",
            "is_main": 1,
            "created_at": ts,
        },
    )
    episode_id = db.insert(
        "episodes",
        {
            "project_id": project_id,
            "branch_id": branch_id,
            "number": 1,
            "title": "Screenplay",
            "logline": "",
            "status": "Draft",
            "created_at": ts,
            "updated_at": ts,
        },
    )

    scenes = parsed["scenes"] or [{"slugline": "", "screenplay_text": ""}]
    for index, scene in enumerate(scenes, start=1):
        db.insert(
            "scenes",
            {
                "episode_id": episode_id,
                "scene_no": index,
                "slugline": scene.get("slugline", ""),
                "pov_character_id": None,
                "opening_behavior": "",
                "scene_want": "",
                "obstacle": "",
                "tactic": "",
                "pressure": "",
                "choice": "",
                "start_state": "",
                "end_state": "",
                "cut_on": "",
                "notes": "",
                "screenplay_text": scene.get("screenplay_text", ""),
                "moral_delta": 0,
                "created_at": ts,
                "updated_at": ts,
            },
        )

    parents = meta.get("parents") or []
    parent_id = parents[0] if parents else None
    sidecar_name = f"{Path(name).stem}.pressureroom"

    db.upsert_project_source(
        project_id,
        source_kind="fountain",
        drive_file_id=file_id,
        drive_file_name=name,
        drive_parent_id=parent_id,
        sidecar_file_id=None,
        sidecar_file_name=sidecar_name,
        fountain_preamble=parsed["preamble"],
        screenplay_hash=screenplay_hash(project_id),
        source_modified_time=str(meta.get("modifiedTime", "")),
        linked_at=ts,
        updated_at=ts,
    )

    # Creates the companion sidecar, preferably beside the Fountain file.
    drive_store.save_project(session, project_id)

    return {
        "project_id": project_id,
        "linked": True,
        "already_linked": False,
        "file_name": name,
        "scene_count": len(scenes),
        "sidecar_name": sidecar_name,
    }


def sync_to_fountain(session: dict, project_id: str) -> dict | None:
    source = db.get_project_source(project_id)
    if not source or source.get("source_kind") != "fountain":
        return None

    current_hash = screenplay_hash(project_id)
    if current_hash == (source.get("screenplay_hash") or ""):
        return {"updated": False, "file_name": source.get("drive_file_name", "")}

    text = _render_linked_fountain(project_id, source.get("fountain_preamble", ""))
    drive_store.upload_text(session, source["drive_file_id"], text)
    meta = drive_store.file_metadata(session, source["drive_file_id"])

    db.upsert_project_source(
        project_id,
        screenplay_hash=current_hash,
        source_modified_time=str(meta.get("modifiedTime", "")),
        updated_at=db.now_iso(),
    )

    return {
        "updated": True,
        "file_name": source.get("drive_file_name", ""),
    }
