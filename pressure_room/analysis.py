from __future__ import annotations
import math
from collections import Counter

PRESSURE_MOVES = {
    "Remove an option": "Take away the protagonist's easiest escape route.",
    "Add a deadline": "Make delay itself costly.",
    "Conflicting obligations": "Force two values or promises to collide.",
    "Expose prior behavior": "Let an earlier choice become evidence.",
    "Reverse status": "Give leverage to someone the protagonist underestimated.",
    "Force commitment": "Make half-measures impossible.",
    "Create a witness": "Let someone see what was supposed to remain private.",
    "Attach collateral": "Make solving the problem hurt someone the character values.",
}

def scene_health(scene: dict) -> list[str]:
    notes = []
    if not (scene.get("start_state") or "").strip() or not (scene.get("end_state") or "").strip():
        notes.append("Define both the starting and ending state.")
    elif scene.get("start_state", "").strip().lower() == scene.get("end_state", "").strip().lower():
        notes.append("The scene appears to reset rather than transform the story.")
    if not (scene.get("choice") or "").strip():
        notes.append("No decisive choice is recorded.")
    if not (scene.get("pressure") or "").strip():
        notes.append("Pressure is undefined; ask what narrows the character's options.")
    if not (scene.get("cut_on") or "").strip():
        notes.append("Consider ending on a decision, reveal, or irreversible change.")
    return notes

def story_mri(scenes: list[dict], bills: list[dict]) -> list[dict]:
    outstanding = sum(1 for b in bills if b["status"] in ("Outstanding","Escalating"))
    running_pressure = 0
    running_moral = 0
    out = []
    for i, s in enumerate(scenes, start=1):
        pressure_components = sum(bool((s.get(k) or "").strip()) for k in ("obstacle","pressure","choice"))
        running_pressure = min(10, max(1, round((running_pressure * 0.55) + pressure_components * 1.6 + i * 0.3)))
        running_moral = max(0, min(10, running_moral + int(s.get("moral_delta") or 0)))
        option_space = max(1, 10 - round(running_pressure * .55) - min(3, outstanding // 2))
        out.append({
            "scene": f"S{s['scene_no']}",
            "pressure": running_pressure,
            "moral_compromise": running_moral,
            "option_space": option_space,
        })
    return out

def writers_room_questions(project: dict, character: dict | None, scenes: list[dict], bills: list[dict]) -> list[str]:
    q = []
    outstanding = [b for b in bills if b["status"] in ("Outstanding","Escalating")]
    if character:
        boundary = character.get("moral_boundary") or "their stated boundary"
        q.append(f"What pressure would make {character['name']} seriously consider violating: “{boundary}”?")
        q.append(f"Why can't {character['name']} simply tell the truth or walk away?")
    if outstanding:
        oldest = outstanding[-1]
        q.append(f"Could the outstanding bill “{oldest['title']}” complicate the next solution instead of introducing a new problem?")
    if scenes:
        last = scenes[-1]
        q.append(f"Because Scene {last['scene_no']} ends with “{last.get('choice') or 'a choice'},” what must now be true?")
        if scene_health(last):
            q.append("What is concretely different at the end of the latest scene—knowledge, status, relationship, danger, objective, or moral state?")
    q.append("Which current solution is working too well, and how can the story make that solution stop working?")
    q.append("What choice would be surprising to the audience but inevitable for this character?")
    return q[:6]
