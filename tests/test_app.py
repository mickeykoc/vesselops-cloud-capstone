import json
from unittest.mock import patch
import pytest
from app import create_app
from app.store import Conflict, SQLiteStore


def make_ticket(client, auth):
    response = client.post(
        "/api/tickets", headers=auth, json={"title": "VPN login fails", "priority": "P2", "category": "access"}
    )
    assert response.status_code == 201
    return response.json


def test_fail_closed_without_token(tmp_path):
    with pytest.raises(ValueError):
        create_app({"API_TOKEN": "", "SQLITE_PATH": str(tmp_path / "db")})


def test_unknown_mode():
    with pytest.raises(ValueError):
        create_app({"APP_MODE": "typo"})


@pytest.mark.parametrize("path", ["/api/state", "/health/ready"])
def test_read_routes_require_auth(client, path):
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"].startswith("Bearer")


@pytest.mark.parametrize("path", ["/api/tickets", "/api/assets", "/api/incidents"])
def test_write_routes_require_auth(client, path):
    assert client.post(path, json={}).status_code == 401


def test_live_is_public_but_not_data(client):
    assert client.get("/health/live").json == {"status": "alive", "mode": "local"}
    assert client.get("/").status_code == 200
    assert b"Operator access" in client.get("/").data


def test_security_headers(client):
    response = client.get("/")
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Cache-Control"] == "no-store"
    assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    assert response.headers["X-Request-ID"]


def test_asset_link_and_ticket_lifecycle(client, auth):
    asset = client.post("/api/assets", headers=auth, json={"tag": "LAB-1", "hostname": "pc", "owner": "Demo"})
    assert asset.status_code == 201
    ticket = client.post(
        "/api/tickets",
        headers=auth,
        json={"title": "DNS issue", "priority": "P1", "category": "network", "asset_id": "LAB-1"},
    ).json
    for status in ("in_progress", "resolved", "open"):
        response = client.patch(
            "/api/tickets/" + ticket["id"],
            headers=auth,
            json={"version": ticket["version"], "status": status, "note": "Documented diagnostic step"},
        )
        assert response.status_code == 200
        ticket = response.json
    assert len(ticket["history"]) == 4
    result = client.get("/api/state", headers=auth).json
    assert result["summary"]["active"] == 1
    assert len(result["assets"]) == 1


def test_stale_update_rejected(client, auth):
    ticket = make_ticket(client, auth)
    body = {"version": ticket["version"], "status": "in_progress", "note": "Checking"}
    assert client.patch("/api/tickets/" + ticket["id"], headers=auth, json=body).status_code == 200
    assert client.patch("/api/tickets/" + ticket["id"], headers=auth, json=body).status_code == 409


def test_sqlite_compare_and_swap(tmp_path):
    store = SQLiteStore(tmp_path / "race.db")
    document = store.create({"id": "1", "kind": "asset", "hostname": "first"})
    stale = dict(document, hostname="stale")
    store.replace(dict(document, hostname="fresh"), document["version"])
    with pytest.raises(Conflict):
        store.replace(stale, document["version"])
    assert store.get("asset", "1")["hostname"] == "fresh"


def test_duplicate_asset(client, auth):
    data = {"tag": "LAB-1", "hostname": "pc", "owner": "Demo"}
    assert client.post("/api/assets", headers=auth, json=data).status_code == 201
    assert client.post("/api/assets", headers=auth, json=data).status_code == 409


def test_missing_link_returns_404(client, auth):
    response = client.post(
        "/api/tickets",
        headers=auth,
        json={"title": "Test", "priority": "P2", "category": "access", "asset_id": "missing"},
    )
    assert response.status_code == 404


def test_skip_workflow_rejected(client, auth):
    ticket = make_ticket(client, auth)
    assert (
        client.patch(
            "/api/tickets/" + ticket["id"],
            headers=auth,
            json={"version": ticket["version"], "status": "resolved", "note": "Skipping"},
        ).status_code
        == 400
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"priority": "P0"},
        {"category": "unknown"},
        {"title": "x" * 161},
        {"unexpected": True},
        {"asset_id": 123},
    ],
)
def test_bad_ticket_input(client, auth, overrides):
    body = {"title": "Test", "priority": "P3", "category": "access", **overrides}
    assert client.post("/api/tickets", headers=auth, json=body).status_code == 400


def test_non_object_json_and_large_request(client, auth):
    assert client.post("/api/tickets", headers=auth, json=[]).status_code == 400
    assert (
        client.post("/api/tickets", headers=auth, data="x" * 40000, content_type="application/json").status_code == 413
    )


def test_incident_requires_evidence(client, auth):
    data = {
        "title": "Review",
        "severity": "medium",
        "source": "synthetic",
        "event_ids": [],
        "summary": "Controlled scenario",
    }
    assert client.post("/api/incidents", headers=auth, json=data).status_code == 400
    data["event_ids"] = ["request-1"]
    assert client.post("/api/incidents", headers=auth, json=data).status_code == 201
    assert client.get("/api/state", headers=auth).json["summary"]["incidents"] == 1


def test_readiness_failure_does_not_leak_exception(client, app, auth):
    with patch.object(app.extensions["store"], "healthy", side_effect=RuntimeError("super-secret-password")):
        response = client.get("/health/ready", headers=auth)
    assert response.status_code == 503
    assert b"super-secret" not in response.data


def test_logging_does_not_record_token_or_body(client, auth):
    with patch("app.AUDIT.info") as log:
        client.get("/api/state", headers={"Authorization": "Bearer secret-not-to-log"})
        event = json.loads(log.call_args.args[0])
        assert event["event"] == "auth.failed"
        assert "secret-not-to-log" not in log.call_args.args[0]


def test_database_text_preserved_not_executed(client, auth):
    title = "'); DROP TABLE documents; -- <script>alert(1)</script>"
    response = client.post(
        "/api/tickets", headers=auth, json={"title": title, "priority": "P3", "category": "application"}
    )
    assert response.status_code == 201
    assert client.get("/api/state", headers=auth).json["tickets"][0]["title"] == title


def test_azure_configuration_without_cloud_uses_injected_store(tmp_path):
    azure = create_app({"APP_MODE": "azure", "API_TOKEN": "x" * 48}, store=SQLiteStore(tmp_path / "injected.db"))
    assert azure.test_client().get("/").headers["Strict-Transport-Security"].startswith("max-age=")
