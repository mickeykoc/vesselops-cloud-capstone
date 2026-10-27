"""Optional local browser verification; all records are synthetic."""

from pathlib import Path
import sys
import threading
import tempfile
import json
import secrets

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app import create_app  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402
from tools.scenario import execute  # noqa: E402

root = ROOT
with tempfile.TemporaryDirectory() as tmp:
    token = secrets.token_urlsafe(36)
    app = create_app({"APP_MODE": "local", "API_TOKEN": token, "SQLITE_PATH": str(Path(tmp) / "db")})
    server = make_server("127.0.0.1", 8088, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    scenario = execute("http://127.0.0.1:8088", token)
    (root / "evidence/local_scenario.json").write_text(json.dumps(scenario, indent=2) + "\n")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1120}, device_scale_factor=1)
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.goto("http://127.0.0.1:8088")
        page.get_by_label("Operator token", exact=True).fill(token)
        page.get_by_role("button", name="Connect", exact=False).click()
        page.get_by_text("Operator session active. Records loaded.").wait_for()
        assert page.locator("#metric-incidents").inner_text() == "1"
        assert page.locator("#metric-assets").inner_text() == "1"
        # Create a second case through the real browser UI.
        page.get_by_text("+ Open a support ticket").click()
        page.locator("#ticket-form input[name=title]").fill("VPN access fails after password reset")
        page.locator("#ticket-form select[name=priority]").select_option("P2")
        page.get_by_role("button", name="Create ticket", exact=True).click()
        page.get_by_text("Record created.", exact=True).wait_for()
        assert page.locator("#metric-active").inner_text() == "1"
        page.get_by_role("button", name="Review →").first.click()
        page.locator("#update-note").fill("Checked synthetic account state and reproduced cached credential failure.")
        page.get_by_role("button", name="Save update").click()
        page.get_by_text("Ticket updated. Investigation history preserved.").wait_for()
        page.locator("span.badge.in_progress").wait_for()
        page.locator("#ticket-form").evaluate('(e)=>e.closest("details").open=false')
        page.screenshot(path=str(root / "docs/console.png"), full_page=True)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(root / "docs/console_mobile.png"), full_page=True)
        page.get_by_role("button", name="Lock", exact=True).click()
        assert page.locator("#metric-active").inner_text() == "—"
        assert page.locator("#ticket-rows").inner_text() == ""
        assert not errors, errors
        browser.close()
    server.shutdown()
(root / "evidence/browser_checks.json").write_text(
    json.dumps(
        {
            "status": "passed",
            "environment": "local SQLite with synthetic records",
            "checks": [
                "operator connect",
                "scenario evidence visible",
                "create ticket through UI",
                "review and update ticket",
                "desktop screenshot",
                "390px mobile no horizontal overflow",
                "lock clears operational records",
                "no JavaScript page errors",
            ],
            "cloud_deployment": False,
        },
        indent=2,
    )
    + "\n"
)
print("Local scenario and browser checks passed")
