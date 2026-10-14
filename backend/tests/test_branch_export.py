"""PDFs contain one story path; editable Fountain/backup remain full-project."""

from app.branch_export import pdf_branch_payload
from app.exporters import fountain


def sample_project():
    return {
        "project": {"title": "Branches"},
        "branches": [
            {"id": "main", "is_main": 1},
            {"id": "fork", "is_main": 0, "parent_branch_id": "main"},
            {"id": "other", "is_main": 0, "parent_branch_id": "main"},
        ],
        "episodes": [
            {"id": "ep-main", "branch_id": "main", "number": 1, "title": "Main"},
            {"id": "ep-fork", "branch_id": "fork", "number": 1, "title": "Fork"},
            {"id": "ep-other", "branch_id": "other", "number": 1, "title": "Other"},
        ],
        "scenes": [
            {"id": "main-intro", "episode_id": "ep-main", "scene_no": 1, "slugline": "MAIN INTRO"},
            {"id": "main-end", "episode_id": "ep-main", "scene_no": 2, "slugline": "MAIN END"},
            {"id": "fork-intro", "episode_id": "ep-fork", "scene_no": 1, "slugline": "SHARED INTRO"},
            {"id": "fork-end", "episode_id": "ep-fork", "scene_no": 2, "slugline": "FORK END"},
            {"id": "other-intro", "episode_id": "ep-other", "scene_no": 1, "slugline": "OTHER INTRO"},
        ],
        "causal_links": [
            {"id": "l-main", "episode_id": "ep-main"},
            {"id": "l-fork", "episode_id": "ep-fork"},
            {"id": "l-other", "episode_id": "ep-other"},
        ],
        "bills": [
            {"id": "bm", "episode_id": "ep-main", "title": "Main bill"},
            {"id": "bf", "episode_id": "ep-fork", "title": "Fork bill"},
            {"id": "bo", "episode_id": "ep-other", "title": "Other bill"},
            {"id": "b-global", "episode_id": None, "title": "Global bill"},
        ],
        "story_notes": [
            {"object_type": "scene", "object_id": "main-end"},
            {"object_type": "scene", "object_id": "fork-end"},
            {"object_type": "project", "object_id": "p"},
        ],
    }


def test_selected_pdf_has_cloned_common_opening_but_no_other_paths():
    whole = sample_project()
    result = pdf_branch_payload(whole, "fork")
    assert [e["id"] for e in result["episodes"]] == ["ep-fork"]
    assert [s["slugline"] for s in result["scenes"]] == ["SHARED INTRO", "FORK END"]
    assert [l["id"] for l in result["causal_links"]] == ["l-fork"]
    assert {b["id"] for b in result["bills"]} == {"bf", "b-global"}
    assert {n["object_id"] for n in result["story_notes"]} == {"fork-end", "p"}
    assert len(whole["scenes"]) == 5  # Never mutate full backup/Fountain state.
    assert "MAIN END" in fountain(whole) and "FORK END" in fountain(whole)


def test_default_pdf_is_main_and_unknown_branch_is_rejected():
    import pytest
    whole = sample_project()
    assert [e["id"] for e in pdf_branch_payload(whole)["episodes"]] == ["ep-main"]
    with pytest.raises(ValueError, match="Story branch not found"):
        pdf_branch_payload(whole, "a different project's branch")
