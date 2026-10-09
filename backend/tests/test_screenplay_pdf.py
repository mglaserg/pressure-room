"""PDF exports preserve screenplay structure without including author's private notes."""
from app.screenplay_pdf import fountain_blocks, screenplay_pdf_bytes


def test_fountain_blocks_classify_dialogue_and_skip_notes():
    sample = """[[private note]]
.INT. OFFICE - DAY

@AMBER
(quietly)
Tell me.

>FADE OUT:
"""
    blocks = list(fountain_blocks(sample))
    assert ("scene", "INT. OFFICE - DAY") in blocks
    assert ("character", "AMBER") in blocks
    assert ("parenthetical", "(quietly)") in blocks
    assert ("dialogue", "Tell me.") in blocks
    assert ("transition", "FADE OUT:") in blocks
    assert ("note", "[[private note]]") in blocks


def test_screenplay_pdf_generates_both_layouts_and_empty_story():
    payload = {
        "project": {"title": "Flowers & Amber"},
        "episodes": [{"id": "episode", "number": 1, "title": "Pilot"}],
        "scenes": [{"episode_id": "episode", "scene_no": 1, "slugline": "INT. OFFICE - DAY",
                    "screenplay_text": "AMBER\nTell me about the flowers.\n\n[[PRIVATE NOTE]]"}],
    }
    for mobile in (True, False):
        data = screenplay_pdf_bytes(payload, mobile=mobile)
        assert data.startswith(b"%PDF-")
        assert len(data) > 1000
    empty = screenplay_pdf_bytes({"project": {"title": "Empty"}, "episodes": [], "scenes": []})
    assert empty.startswith(b"%PDF-")
