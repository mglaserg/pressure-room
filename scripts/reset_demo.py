from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pressure_room import db

if db.DB_PATH.exists():
    db.DB_PATH.unlink()
db.init_db()
print(f"Reset Pressure Room database at: {db.DB_PATH}")
