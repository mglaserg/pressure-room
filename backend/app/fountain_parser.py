"""Parse portable Fountain text without remote integrations."""
import re
from pathlib import Path

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
