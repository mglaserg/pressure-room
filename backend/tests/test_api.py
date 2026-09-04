import os
from pathlib import Path

TEST_DB = Path(__file__).with_name("test_pressure_room.db")
os.environ["PRESSURE_ROOM_DB"] = str(TEST_DB)

from fastapi.testclient import TestClient
from app import db
from app.main import app
from app.exporters import read_package


def setup_module():
    if TEST_DB.exists():
        TEST_DB.unlink()
    db.DB_PATH = TEST_DB
    db.init_db(seed=True)


def teardown_module():
    if TEST_DB.exists():
        TEST_DB.unlink()


def test_workspace_export_and_import():
    with TestClient(app) as client:
        projects = client.get("/api/projects").json()
        assert projects
        pid = projects[0]["id"]
        workspace = client.get(f"/api/projects/{pid}").json()
        assert workspace["project"]["title"] == "The Last Favor"
        ep = workspace["episodes"][0]
        diagnostics = client.get(f"/api/episodes/{ep['id']}/diagnostics").json()
        assert diagnostics["mri"]
        export = client.get(f"/api/projects/{pid}/export/package")
        assert export.status_code == 200
        payload = read_package(export.content)
        assert payload["format"] == "pressure-room"
        imported = client.post("/api/import?mode=copy", files={"file": ("story.pressureroom", export.content, "application/zip")})
        assert imported.status_code == 200
        assert imported.json()["project_id"] != pid


def test_screenplay_update_and_snapshot():
    with TestClient(app) as client:
        pid = client.get("/api/projects").json()[0]["id"]
        ws = client.get(f"/api/projects/{pid}").json()
        sid = ws["scenes"][0]["id"]
        r = client.patch(f"/api/scenes/{sid}", json={"data": {"screenplay_text": "INT. TEST — DAY\n\nA choice is made."}})
        assert r.status_code == 200
        snap = client.post(f"/api/projects/{pid}/snapshots", json={"label": "Before rewrite"})
        assert snap.status_code == 200


def test_pdf_branch_and_snapshot():
    with TestClient(app) as client:
        pid = client.get("/api/projects").json()[0]["id"]
        ws = client.get(f"/api/projects/{pid}").json()
        main = next(b for b in ws["branches"] if b["is_main"])
        pdf = client.get(f"/api/projects/{pid}/export/pdf")
        assert pdf.status_code == 200
        assert pdf.content.startswith(b"%PDF-")
        branched = client.post(f"/api/projects/{pid}/branches/{main['id']}/clone", json={"name": "What if Mara refuses?"})
        assert branched.status_code == 200
        snap = client.post(f"/api/projects/{pid}/snapshots", json={"label": "Story lab checkpoint"})
        assert snap.status_code == 200
        refreshed = client.get(f"/api/projects/{pid}").json()
        assert any(b["name"] == "What if Mara refuses?" for b in refreshed["branches"])
        assert any(s["label"] == "Story lab checkpoint" for s in refreshed["snapshots"])


def test_patch_field_whitelist():
    with TestClient(app) as client:
        pid = client.get("/api/projects").json()[0]["id"]
        rejected = client.patch(f"/api/projects/{pid}", json={"data": {"definitely_not_a_column": "x"}})
        assert rejected.status_code == 400


def test_character_patch_accepts_editable_fields_and_rejects_record_metadata():
    with TestClient(app) as client:
        pid = client.get("/api/projects").json()[0]["id"]
        ws = client.get(f"/api/projects/{pid}").json()
        cid = ws["characters"][0]["id"]
        ok = client.patch(f"/api/characters/{cid}", json={"data": {
            "name": "Mara Vale Revised",
            "role": "Protagonist",
            "want": "Win without losing herself.",
            "moral_boundary": "Never fabricate evidence.",
            "moral_score": 3,
        }})
        assert ok.status_code == 200
        bad = client.patch(f"/api/characters/{cid}", json={"data": {"id": cid, "name": "Nope"}})
        assert bad.status_code == 400


def test_causal_link_validation_is_clear_and_duplicate_safe():
    with TestClient(app) as client:
        pid = client.get("/api/projects").json()[0]["id"]
        ws = client.get(f"/api/projects/{pid}").json()
        ep = ws["episodes"][0]
        scenes = sorted([s for s in ws["scenes"] if s["episode_id"] == ep["id"]], key=lambda s: s["scene_no"])
        assert len(scenes) >= 2

        self_link = client.post(f"/api/episodes/{ep['id']}/links", json={"data": {
            "from_scene_id": scenes[0]["id"], "relation": "THEREFORE", "to_scene_id": scenes[0]["id"], "note": "no"
        }})
        assert self_link.status_code == 400
        assert "cannot cause itself" in self_link.json()["detail"]

        relation = "THEREFORE"
        while any(l["from_scene_id"] == scenes[0]["id"] and l["to_scene_id"] == scenes[1]["id"] and l["relation"] == relation for l in ws["causal_links"]):
            relation = "BUT" if relation == "THEREFORE" else "THEREFORE"
            if any(l["from_scene_id"] == scenes[0]["id"] and l["to_scene_id"] == scenes[1]["id"] and l["relation"] == relation for l in ws["causal_links"]):
                break
        payload = {"from_scene_id": scenes[0]["id"], "relation": relation, "to_scene_id": scenes[1]["id"], "note": "This choice forces the next scene."}
        first = client.post(f"/api/episodes/{ep['id']}/links", json={"data": payload})
        if first.status_code == 200:
            duplicate = client.post(f"/api/episodes/{ep['id']}/links", json={"data": payload})
            assert duplicate.status_code == 400
            assert "already exists" in duplicate.json()["detail"]
