from app.fountain_link import parse_fountain


def test_parse_fountain_title_and_scenes():
    raw = """Title: The Last Passenger
Author: A Writer

INT. DINER - NIGHT

MARA sits alone.

MARA
I thought you'd never come.

EXT. STREET - NIGHT

Rain.
"""
    parsed = parse_fountain(raw, "fallback.fountain")
    assert parsed["title"] == "The Last Passenger"
    assert len(parsed["scenes"]) == 2
    assert parsed["scenes"][0]["slugline"] == "INT. DINER - NIGHT"
    assert "I thought you'd never come." in parsed["scenes"][0]["screenplay_text"]
    assert parsed["scenes"][1]["slugline"] == "EXT. STREET - NIGHT"
