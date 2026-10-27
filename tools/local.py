"""Start a localhost-only lab; token is generated for this session."""

import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app  # noqa: E402

if __name__ == "__main__":
    token = os.environ.get("API_TOKEN") or secrets.token_urlsafe(36)
    print("\nVesselOps local lab → http://127.0.0.1:8080", flush=True)
    print("Paste this session token into the console:", token, flush=True)
    app = create_app({"APP_MODE": "local", "API_TOKEN": token, "SQLITE_PATH": str(ROOT / "data/local.db")})
    app.run(host="127.0.0.1", port=8080, debug=False)
