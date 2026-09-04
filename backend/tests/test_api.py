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
