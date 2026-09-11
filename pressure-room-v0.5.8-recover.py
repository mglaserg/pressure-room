#!/usr/bin/env python3
# Pressure Room v0.5.8 partial-upgrade recovery.
#
# Use this only after the first v0.5.8 upgrader failed with:
#   NameError: name 'r' is not defined
#
# Run from:
#   C:\Users\mglas\Documents\GitHub\pressure-room
#
# Command:
#   python .\pressure-room-v0.5.8-recover.py

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path.cwd()

DB = Path("backend/app/db.py")
DRIVE = Path("backend/app/drive_store.py")
MAIN = Path("backend/app/main.py")
ENV_EXAMPLE = Path("backend/.env.example")
TESTS = Path("backend/tests/test_api.py")
WORKFLOW = Path(".github/workflows/deploy-backend-ecs-express.yml")
ALL = [DB, DRIVE, MAIN, ENV_EXAMPLE, TESTS, WORKFLOW]


def die(message: str) -> None:
    print("\nERROR: " + message, file=sys.stderr)
    raise SystemExit(1)


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def read(path: Path) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    (ROOT / path).write_text(text, encoding="utf-8", newline="\n")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        die(f"{label}: expected exactly one match, found {count}.")
    return text.replace(old, new, 1)


def preflight() -> None:
    if not (ROOT / ".git").exists():
        die(r"Run this from C:\Users\mglas\Documents\GitHub\pressure-room")
    for path in ALL:
        if not (ROOT / path).exists():
            die(f"Missing expected file: {path}")


def verify_partial_upgrade() -> None:
    db = read(DB)
    drive = read(DRIVE)
    main = read(MAIN)
    env = read(ENV_EXAMPLE)

    problems = []

    if "def bind_user_cache(" not in db:
        problems.append("backend/app/db.py is missing bind_user_cache()")
    if "def _bind_user_cache(" not in drive:
        problems.append("backend/app/drive_store.py is missing _bind_user_cache()")
    if "PRESSURE_ROOM_ALLOWED_EMAIL" in drive or "ALLOWED_EMAIL" in drive:
        problems.append("drive_store.py still contains the single-user email allowlist")
    if 'version="0.5.8"' not in main or '"version": "0.5.8"' not in main:
        problems.append("backend/app/main.py is not at v0.5.8")
    if "PRESSURE_ROOM_ALLOWED_EMAIL" in env:
        problems.append("backend/.env.example still contains PRESSURE_ROOM_ALLOWED_EMAIL")

    if problems:
        die(
            "Repo is not in the expected partial-upgrade state:\n  - "
            + "\n  - ".join(problems)
            + "\n\nDo not reset anything; send me this output."
        )


def patch_tests() -> None:
    text = read(TESTS)

    if "def test_google_user_caches_are_isolated(" in text:
        print("Tests: cache-isolation test already present.")
        return

    addition = '''

def test_google_user_caches_are_isolated(tmp_path, monkeypatch):
    \"\"\"Two Google users must never share the same ephemeral SQLite cache.\"\"\"
    monkeypatch.setenv(
        "PRESSURE_ROOM_USER_CACHE_DIR",
        str(tmp_path / "user-cache"),
    )

    try:
        path_a = db.bind_user_cache("google-sub-user-a")
        db.clear_projects()

        ts = db.now_iso()
        project_a = db.insert(
            "projects",
            {
                "title": "User A Story",
                "premise": "",
                "theme": "",
                "created_at": ts,
                "updated_at": ts,
            },
        )

        path_b = db.bind_user_cache("google-sub-user-b")
        assert path_b != path_a
        assert db.get_projects() == []

        ts = db.now_iso()
        db.insert(
            "projects",
            {
                "title": "User B Story",
                "premise": "",
                "theme": "",
                "created_at": ts,
                "updated_at": ts,
            },
        )
        assert [p["title"] for p in db.get_projects()] == ["User B Story"]

        db.bind_user_cache("google-sub-user-a")
        projects_a = db.get_projects()
        assert [p["id"] for p in projects_a] == [project_a]
        assert [p["title"] for p in projects_a] == ["User A Story"]
    finally:
        db.bind_default_cache()
'''

    write(TESTS, text.rstrip() + addition.rstrip() + "\n")
    print("Tests: added per-user cache isolation regression test.")


def patch_workflow() -> None:
    text = read(WORKFLOW)

    old_env = '''env:
  AWS_REGION: us-east-2
  ECR_REPOSITORY: ${{ vars.ECR_REPOSITORY }}
  ECS_SERVICE: ${{ vars.ECS_SERVICE }}
  ECS_CLUSTER: ${{ vars.ECS_CLUSTER }}
'''

    new_env = '''env:
  AWS_REGION: us-east-2
  ECR_REPOSITORY: pressure-room-api
  ECS_SERVICE: pressure-room-api-c5dc
  ECS_CLUSTER: default
'''

    if old_env in text:
        text = text.replace(old_env, new_env, 1)
    elif new_env not in text:
        die("Workflow ECS environment block is not in a recognized state.")

    checkout = '''      - name: Checkout
        uses: actions/checkout@v7
'''

    preflight = '''      - name: Checkout
        uses: actions/checkout@v7

      - name: Validate production deployment configuration
        shell: bash
        env:
          AWS_DEPLOY_ROLE_ARN: ${{ vars.AWS_DEPLOY_ROLE_ARN }}
          ECS_EXECUTION_ROLE_ARN: ${{ vars.ECS_EXECUTION_ROLE_ARN }}
          ECS_INFRASTRUCTURE_ROLE_ARN: ${{ vars.ECS_INFRASTRUCTURE_ROLE_ARN }}
          GOOGLE_CLIENT_ID: ${{ vars.GOOGLE_CLIENT_ID }}
          GOOGLE_CLIENT_SECRET_ARN: ${{ vars.GOOGLE_CLIENT_SECRET_ARN }}
          PRESSURE_ROOM_SESSION_KEY_ARN: ${{ vars.PRESSURE_ROOM_SESSION_KEY_ARN }}
          PRESSURE_ROOM_PUBLIC_URL: ${{ vars.PRESSURE_ROOM_PUBLIC_URL }}
        run: |
          required=(
            AWS_DEPLOY_ROLE_ARN
            ECS_EXECUTION_ROLE_ARN
            ECS_INFRASTRUCTURE_ROLE_ARN
            GOOGLE_CLIENT_ID
            GOOGLE_CLIENT_SECRET_ARN
            PRESSURE_ROOM_SESSION_KEY_ARN
            PRESSURE_ROOM_PUBLIC_URL
          )

          missing=()
          for name in "${required[@]}"; do
            if [[ -z "${!name}" ]]; then
              missing+=("$name")
            fi
          done

          if ((${#missing[@]})); then
            printf 'Missing production environment variable: %s\\n' "${missing[@]}"
            exit 1
          fi
'''

    if "Validate production deployment configuration" not in text:
        text = replace_once(
            text,
            checkout,
            preflight,
            "workflow preflight insertion",
        )

    allowlist = '''              {
                "name": "PRESSURE_ROOM_PUBLIC_URL",
                "value": "${{ vars.PRESSURE_ROOM_PUBLIC_URL }}"
              },
              {
                "name": "PRESSURE_ROOM_ALLOWED_EMAIL",
                "value": "${{ vars.PRESSURE_ROOM_ALLOWED_EMAIL }}"
              }
'''

    public_url_only = '''              {
                "name": "PRESSURE_ROOM_PUBLIC_URL",
                "value": "${{ vars.PRESSURE_ROOM_PUBLIC_URL }}"
              }
'''

    if allowlist in text:
        text = text.replace(allowlist, public_url_only, 1)

    if "PRESSURE_ROOM_ALLOWED_EMAIL" in text:
        die("Workflow still contains PRESSURE_ROOM_ALLOWED_EMAIL.")

    write(WORKFLOW, text)
    print("Workflow: fixed ECS identifiers, removed email gate, added preflight.")


def validate() -> None:
    py_files = [
        str(DB),
        str(DRIVE),
        str(MAIN),
        str(TESTS),
    ]

    result = run(sys.executable, "-m", "py_compile", *py_files)
    if result.returncode != 0:
        die("Python compile failed:\n" + (result.stderr or result.stdout))

    result = run("git", "diff", "--check", "--", *map(str, ALL))
    if result.returncode != 0:
        die("git diff --check failed:\n" + (result.stdout or result.stderr))

    workflow = read(WORKFLOW)
    required_markers = [
        "ECR_REPOSITORY: pressure-room-api",
        "ECS_SERVICE: pressure-room-api-c5dc",
        "ECS_CLUSTER: default",
        "Validate production deployment configuration",
        "GOOGLE_CLIENT_SECRET_ARN",
        "PRESSURE_ROOM_SESSION_KEY_ARN",
    ]
    missing = [x for x in required_markers if x not in workflow]
    if missing:
        die("Workflow validation failed; missing: " + ", ".join(missing))

    print("Validation: Python compile PASS")
    print("Validation: git diff --check PASS")
    print("Validation: workflow markers PASS")


def main() -> None:
    preflight()
    verify_partial_upgrade()
    patch_tests()
    patch_workflow()
    validate()

    print("\nRecovery complete.")
    print("\nNow run:")
    print("  cd backend")
    print("  uv run pytest -q")
    print("  cd ..")
    print("  git diff --check")
    print("  git status")
    print("  git diff --stat")


if __name__ == "__main__":
    main()
