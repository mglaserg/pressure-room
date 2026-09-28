from __future__ import annotations

PRESSURE_MOVES = [
    ("Remove an option", "Take away the protagonist's easiest escape route."),
    ("Add a deadline", "Make delay itself costly."),
    ("Conflicting obligations", "Force two values or promises to collide."),
    ("Expose prior behavior", "Let an earlier choice become evidence."),
    ("Reverse status", "Give leverage to someone the protagonist underestimated."),
    ("Force commitment", "Make half-measures impossible."),
    ("Create a witness", "Let someone see what was supposed to remain private."),
    ("Attach collateral", "Make solving the problem hurt someone the character values."),
]


def scene_health(scene: dict) -> list[str]:
    notes: list[str] = []
    start, end = (scene.get("start_state") or "").strip(), (scene.get("end_state") or "").strip()
    if not start or not end:
        notes.append("Define both the starting and ending state.")
    elif start.lower() == end.lower():
        notes.append("The scene appears to reset rather than transform the story.")
    if not (scene.get("choice") or "").strip():
        notes.append("No decisive choice is recorded.")
    if not (scene.get("pressure") or "").strip():
        notes.append("Pressure is undefined; ask what narrows the character's options.")
    if not (scene.get("cut_on") or "").strip():
        notes.append("Consider ending on a decision, reveal, or irreversible change.")
    return notes


def story_mri(scenes: list[dict], bills: list[dict]) -> list[dict]:
    outstanding = sum(1 for b in bills if b["status"] in ("Outstanding", "Escalating"))
    running_pressure = 0
    running_moral = 0
    out: list[dict] = []
    for i, scene in enumerate(scenes, start=1):
        components = sum(bool((scene.get(k) or "").strip()) for k in ("obstacle", "pressure", "choice"))
        running_pressure = min(10, max(1, round((running_pressure * 0.55) + components * 1.6 + i * 0.3)))
        running_moral = max(0, min(10, running_moral + int(scene.get("moral_delta") or 0)))
        option_space = max(1, 10 - round(running_pressure * .55) - min(3, outstanding // 2))
        out.append({"scene": f"S{scene['scene_no']}", "pressure": running_pressure, "moral_compromise": running_moral, "option_space": option_space})
    return out


def writers_room_questions(character: dict | None, scenes: list[dict], bills: list[dict]) -> list[str]:
    q: list[str] = []
    outstanding = [b for b in bills if b["status"] in ("Outstanding", "Escalating")]
    if character:
        boundary = character.get("moral_boundary") or "their stated boundary"
        q.append(f"What pressure would make {character['name']} seriously consider violating: ‘{boundary}’?")
        q.append(f"Why can't {character['name']} simply tell the truth or walk away?")
    if outstanding:
        q.append(f"Could the outstanding bill ‘{outstanding[-1]['title']}’ complicate the next solution instead of introducing a new problem?")
    if scenes:
        last = scenes[-1]
        q.append(f"Because Scene {last['scene_no']} ends with ‘{last.get('choice') or 'a choice'},’ what must now be true?")
        if scene_health(last):
            q.append("What is concretely different at the end of the latest scene—knowledge, status, relationship, danger, objective, or moral state?")
    q.append("Which current solution is working too well, and how can the story make that solution stop working?")
    q.append("What choice would be surprising to the audience but inevitable for this character?")
    return q[:6]


def suspense_engine(scenes: list[dict], bills: list[dict], links: list[dict]) -> list[dict]:
    """Describe live audience tension without pretending it is a quality score."""
    ordered = sorted(scenes, key=lambda scene: (int(scene.get("scene_no") or 0), scene.get("created_at") or ""))
    index = {scene.get("id"): i for i, scene in enumerate(ordered)}
    outgoing: dict[str, list[dict]] = {}
    for link in links:
        outgoing.setdefault(link.get("from_scene_id"), []).append(link)

    rows: list[dict] = []
    for i, scene in enumerate(ordered):
        open_bills = []
        paying_off = []
        for bill in bills:
            if bill.get("episode_id") not in {None, scene.get("episode_id")} and bill.get("scene_id") not in index:
                continue
            intro = index.get(bill.get("scene_id"), 0)
            payoff = index.get(bill.get("payoff_scene_id"))
            if payoff == i:
                paying_off.append(bill.get("title") or "Untitled bill")
            if bill.get("status") in {"Outstanding", "Escalating"} and intro <= i and (payoff is None or payoff > i):
                open_bills.append(bill.get("title") or "Untitled bill")

        hooks = []
        if (scene.get("audience_waits_for") or "").strip():
            hooks.append("waiting")
        if (scene.get("withheld_information") or "").strip():
            hooks.append("withheld")
        if (scene.get("audience_knows") or "").strip():
            hooks.append("knowledge gap")
        if open_bills:
            hooks.append("unpaid bill")
        if outgoing.get(scene.get("id")):
            hooks.append("causal handoff")

        rows.append({
            "scene": f"S{scene.get('scene_no')}",
            "scene_id": scene.get("id"),
            "slugline": scene.get("slugline") or "Untitled scene",
            "audience_knows": (scene.get("audience_knows") or "").strip(),
            "audience_waits_for": (scene.get("audience_waits_for") or "").strip(),
            "withheld_information": (scene.get("withheld_information") or "").strip(),
            "open_bills": open_bills,
            "paying_off": paying_off,
            "active_hooks": hooks,
            "handoff": [f"{link.get('relation')} → S{next((s.get('scene_no') for s in ordered if s.get('id') == link.get('to_scene_id')), '?')}" for link in outgoing.get(scene.get("id"), [])],
        })
    return rows
