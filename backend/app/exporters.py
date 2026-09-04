from __future__ import annotations

import io
import json
import zipfile
from html import escape
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak


def project_markdown(payload: dict) -> str:
    p = payload["project"]
    chars = payload.get("characters", [])
    eps = payload.get("episodes", [])
    scenes = payload.get("scenes", [])
    links = payload.get("causal_links", [])
    bills = payload.get("bills", [])
    lines = [f"# {p['title']}", "", p.get("premise", ""), "", f"**Theme:** {p.get('theme','')}", "", "## Characters", ""]
    for c in chars:
        lines += [f"### {c['name']} — {c.get('role','')}", f"- **Want:** {c.get('want','')}", f"- **Need:** {c.get('need','')}", f"- **Moral boundary:** {c.get('moral_boundary','')}", f"- **Core belief:** {c.get('core_belief','')}", f"- **Fear:** {c.get('fear','')}", f"- **Temptation:** {c.get('temptation','')}", ""]
    for ep in eps:
        lines += [f"## E{ep['number']} — {ep['title']}", "", ep.get("logline", ""), ""]
        episode_scenes = [s for s in scenes if s["episode_id"] == ep["id"]]
        for s in episode_scenes:
            lines += [f"### Scene {s['scene_no']} — {s.get('slugline','')}", f"- **Want:** {s.get('scene_want','')}", f"- **Pressure:** {s.get('pressure','')}", f"- **Choice:** {s.get('choice','')}", f"- **Change:** {s.get('start_state','')} → {s.get('end_state','')}", f"- **Cut on:** {s.get('cut_on','')}", ""]
        ep_links = [l for l in links if l["episode_id"] == ep["id"]]
        if ep_links:
            lines += ["### Causal chain", ""]
            for l in ep_links:
                lines.append(f"- S{l.get('from_no','?')} **{l['relation']}** S{l.get('to_no','?')} — {l.get('note','')}")
            lines.append("")
    lines += ["## Bill Ledger", ""]
    for b in bills:
        lines += [f"### {b['title']} — {b['status']}", f"- **External:** {b.get('external_cost','')}", f"- **Moral:** {b.get('moral_cost','')}", ""]
    return "\n".join(lines)


def fountain(payload: dict) -> str:
    p = payload["project"]
    eps = payload.get("episodes", [])
    scenes = payload.get("scenes", [])
    out = [f"Title: {p['title']}", "Credit: Written in Pressure Room", "", ""]
    for ep in eps:
        out += [f"# E{ep['number']} — {ep['title']}", ""]
        for s in [x for x in scenes if x["episode_id"] == ep["id"]]:
            if s.get("slugline"):
                out.append(s["slugline"].upper())
                out.append("")
            if s.get("screenplay_text"):
                out.append(s["screenplay_text"].rstrip())
                out.append("")
    return "\n".join(out)


def package_bytes(payload: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("project.json", json.dumps(payload, ensure_ascii=False, indent=2))
        zf.writestr("story-packet.md", project_markdown(payload))
        zf.writestr("screenplay.fountain", fountain(payload))
        zf.writestr("README.txt", "Pressure Room portable project package. Import this file from Pressure Room's Share menu.\n")
    return buf.getvalue()


def read_package(raw: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(raw)) as zf:
        with zf.open("project.json") as f:
            return json.load(f)


def pdf_bytes(payload: dict) -> bytes:
    p = payload["project"]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=LETTER, rightMargin=48, leftMargin=48, topMargin=48, bottomMargin=48)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="PRTitle", parent=styles["Title"], alignment=TA_CENTER, spaceAfter=18))
    story = [Paragraph(escape(p["title"]), styles["PRTitle"]), Paragraph(escape(p.get("premise", "")), styles["BodyText"]), Spacer(1, 12), Paragraph(f"<b>Theme:</b> {escape(p.get('theme',''))}", styles["BodyText"]), Spacer(1, 18), Paragraph("Characters", styles["Heading1"])]
    for c in payload.get("characters", []):
        story += [Paragraph(escape(f"{c['name']} — {c.get('role','')}"), styles["Heading2"]), Paragraph(f"<b>Want:</b> {escape(c.get('want',''))}", styles["BodyText"]), Paragraph(f"<b>Moral boundary:</b> {escape(c.get('moral_boundary',''))}", styles["BodyText"]), Spacer(1, 8)]
    story.append(PageBreak())
    for ep in payload.get("episodes", []):
        story += [Paragraph(escape(f"E{ep['number']} — {ep['title']}"), styles["Heading1"]), Paragraph(escape(ep.get("logline", "")), styles["BodyText"])]
        for s in [x for x in payload.get("scenes", []) if x["episode_id"] == ep["id"]]:
            story += [Paragraph(escape(f"Scene {s['scene_no']} — {s.get('slugline','')}"), styles["Heading2"]), Paragraph(f"<b>Want:</b> {escape(s.get('scene_want',''))}", styles["BodyText"]), Paragraph(f"<b>Pressure:</b> {escape(s.get('pressure',''))}", styles["BodyText"]), Paragraph(f"<b>Choice:</b> {escape(s.get('choice',''))}", styles["BodyText"]), Spacer(1, 6)]
    story += [PageBreak(), Paragraph("Bill Ledger", styles["Heading1"])]
    for b in payload.get("bills", []):
        story += [Paragraph(escape(f"{b['title']} — {b['status']}"), styles["Heading2"]), Paragraph(f"<b>External:</b> {escape(b.get('external_cost',''))}", styles["BodyText"]), Paragraph(f"<b>Moral:</b> {escape(b.get('moral_cost',''))}", styles["BodyText"]), Spacer(1, 6)]
    doc.build(story)
    return buf.getvalue()
