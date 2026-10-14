"""Select one complete, cloned story path for a PDF reading copy.

Branch cloning copies the parent's episodes and scenes into the child branch.
Consequently the child's own episodes already contain the shared opening, and
we should not add ancestor or sibling episodes to the PDF.
"""


def pdf_branch_payload(payload: dict, branch_id: str | None = None) -> dict:
    """Return a PDF-scoped copy; keep full backup/Fountain payloads unchanged."""
    branches = payload.get("branches", [])
    selected = next((b for b in branches if b.get("id") == branch_id), None) if branch_id else next(
        (b for b in branches if b.get("is_main")), branches[0] if branches else None
    )
    if selected is None:
        raise ValueError("Story branch not found")

    episodes = [e for e in payload.get("episodes", []) if e.get("branch_id") == selected["id"]]
    episode_ids = {e["id"] for e in episodes}
    scenes = [s for s in payload.get("scenes", []) if s.get("episode_id") in episode_ids]
    scene_ids = {s["id"] for s in scenes}
    links = [link for link in payload.get("causal_links", []) if link.get("episode_id") in episode_ids]
    bills = [bill for bill in payload.get("bills", [])
             if (not bill.get("episode_id") or bill["episode_id"] in episode_ids)
             and (not bill.get("scene_id") or bill["scene_id"] in scene_ids)
             and (not bill.get("payoff_scene_id") or bill["payoff_scene_id"] in scene_ids)]
    bill_ids = {bill["id"] for bill in bills}
    scoped_ids = {"episode": episode_ids, "scene": scene_ids, "bill": bill_ids}
    notes = [note for note in payload.get("story_notes", [])
             if note.get("object_type", "").lower() not in scoped_ids
             or note.get("object_id") in scoped_ids[note["object_type"].lower()]]

    return {**payload, "branches": [selected], "episodes": episodes, "scenes": scenes,
            "causal_links": links, "bills": bills, "story_notes": notes}
