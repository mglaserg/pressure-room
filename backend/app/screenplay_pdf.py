"""Typeset saved Fountain scenes as a screenplay PDF (paper or phone edition).

Export is generated from the same persisted scene records as the .fountain export.
Private notes and Fountain sections are omitted from the reading copy.
"""
from __future__ import annotations

import io
import re
from html import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph, PageBreak, SimpleDocTemplate, Spacer

from .fountain_parser import _is_scene_heading

CHARACTER_RE = re.compile(r"^[A-Z0-9][A-Z0-9 .'\"()#\-]+(?:\^)?$")
TRANSITION_RE = re.compile(r"^(?:FADE (?:IN|OUT)\.?|CUT TO:|DISSOLVE TO:|SMASH CUT TO:|MATCH CUT TO:|.+ TO:)$", re.I)


def fountain_blocks(text: str):
    """Classify the subset of Fountain supported by Pressure Room's page view."""
    lines = str(text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    in_dialogue = False
    previous_blank = True
    for index, raw in enumerate(lines):
        line = raw.strip()
        next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
        if not line:
            yield "blank", ""
            previous_blank = True
            in_dialogue = False
        elif (line.startswith("[[") and line.endswith("]]")) or re.match(r"^#{1,6}\s", line) or line.startswith("="):
            yield "note", line
            previous_blank = False
            in_dialogue = False
        elif line.startswith(">") and line.endswith("<") and len(line) > 2:
            yield "centered", line[1:-1].strip()
            previous_blank = False
            in_dialogue = False
        elif _is_scene_heading(line):
            yield "scene", line.lstrip(".").strip()
            previous_blank = False
            in_dialogue = False
        elif (line.startswith(">") and not line.endswith("<")) or TRANSITION_RE.match(line):
            yield "transition", line.lstrip(">").strip()
            previous_blank = False
            in_dialogue = False
        elif line.startswith("@") or (
            previous_blank and bool(next_line) and len(line) <= 42 and CHARACTER_RE.fullmatch(line)
        ):
            yield "character", line.lstrip("@").rstrip("^").strip()
            previous_blank = False
            in_dialogue = True
        elif in_dialogue and line.startswith("(") and line.endswith(")"):
            yield "parenthetical", line
            previous_blank = False
        elif in_dialogue:
            yield "dialogue", line.lstrip("~").strip()
            previous_blank = False
        else:
            yield "action", line.lstrip("!").strip()
            previous_blank = False


def _pdf_styles(mobile: bool):
    face = "Helvetica" if mobile else "Courier"
    bold = "Helvetica-Bold" if mobile else "Courier-Bold"
    size = 12 if mobile else 11.5
    leading = 17 if mobile else 13.5
    base = dict(fontName=face, fontSize=size, leading=leading, textColor=colors.black)
    styles = {
        "action": ParagraphStyle("action", **base, spaceAfter=1),
        "scene": ParagraphStyle("scene", **{**base, "fontName": bold}, spaceBefore=7, spaceAfter=9, keepWithNext=1),
        "character": ParagraphStyle("character", **base, leftIndent=0 if mobile else 132, alignment=TA_CENTER if mobile else 0, spaceBefore=10, keepWithNext=1),
        "parenthetical": ParagraphStyle("parenthetical", **base, leftIndent=22 if mobile else 110, rightIndent=20 if mobile else 100, keepWithNext=1),
        "dialogue": ParagraphStyle("dialogue", **base, leftIndent=12 if mobile else 77, rightIndent=12 if mobile else 64),
        "transition": ParagraphStyle("transition", **base, alignment=TA_RIGHT, spaceBefore=8, spaceAfter=8),
        "centered": ParagraphStyle("centered", **base, alignment=TA_CENTER, spaceBefore=8, spaceAfter=8),
        "episode": ParagraphStyle("episode", fontName=bold, fontSize=10 if mobile else 11, leading=15, spaceAfter=24, alignment=TA_CENTER, textColor=colors.black),
        "title": ParagraphStyle("title", fontName=bold, fontSize=16 if mobile else 18, leading=22, alignment=TA_CENTER, spaceAfter=12, textColor=colors.black),
        "credit": ParagraphStyle("credit", fontName=face, fontSize=10, leading=14, alignment=TA_CENTER, textColor=colors.black),
    }
    return styles


def screenplay_pdf_bytes(payload: dict, mobile: bool = False) -> bytes:
    """PDF reading copy. Mobile uses a narrow page and larger proportional text."""
    buffer = io.BytesIO()
    pagesize = (4.6 * 72, 7.8 * 72) if mobile else LETTER
    margin = 23 if mobile else 62
    doc = SimpleDocTemplate(
        buffer, pagesize=pagesize, leftMargin=margin + (0 if mobile else 28),
        rightMargin=margin, topMargin=32 if mobile else 50,
        bottomMargin=32 if mobile else 48, allowSplitting=1,
        title=f"{payload['project']['title']} - Screenplay",
        author="Pressure Room",
    )
    styles = _pdf_styles(mobile)
    title = str(payload["project"].get("title") or "Untitled Screenplay")
    story = [Spacer(1, 60 if mobile else 140), Paragraph(escape(title), styles["title"]),
             Paragraph("Written in Pressure Room", styles["credit"]), PageBreak()]
    scenes = payload.get("scenes", [])
    episodes = sorted(payload.get("episodes", []), key=lambda e: (str(e.get("branch_id", "")), int(e.get("number", 0))))
    for ep_index, episode in enumerate(episodes):
        part = sorted((s for s in scenes if s.get("episode_id") == episode.get("id")), key=lambda s: int(s.get("scene_no", 0)))
        if not part:
            continue
        if ep_index and len(story) > 4:
            story.append(PageBreak())
        story.append(Paragraph(escape(f"Episode {episode.get('number', '')}: {episode.get('title', '')}"), styles["episode"]))
        for scene in part:
            slug = str(scene.get("slugline") or "").strip()
            body = list(fountain_blocks(scene.get("screenplay_text", "")))
            if slug:
                story.append(Paragraph(escape(slug.upper()), styles["scene"]))
            previous_type = ""
            for kind, line in body:
                if kind == "note":
                    continue
                if kind == "blank":
                    if previous_type != "blank":
                        story.append(Spacer(1, 5 if mobile else 6))
                    previous_type = kind
                    continue
                # Imported Fountain may already contain the scene heading.
                if kind == "scene" and slug and line.upper() == slug.upper():
                    continue
                story.append(Paragraph(escape(line), styles[kind]))
                previous_type = kind
            story.append(Spacer(1, 10 if mobile else 12))
    if len(story) == 4:
        story.append(Paragraph("No screenplay scenes yet.", styles["action"]))

    def footer(canvas, pdf_doc):
        if pdf_doc.page > 1:
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.grey)
            canvas.drawRightString(pagesize[0] - margin, 19, str(pdf_doc.page - 1))
            canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
