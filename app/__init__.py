"""VesselOps: a small operations lab with authenticated APIs and audit events."""

from datetime import datetime, timedelta, timezone
from functools import wraps
import hmac
import json
import logging
import os
import re
import uuid

from flask import Flask, g, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from .store import Conflict, Missing, CosmosStore, SQLiteStore

HOURS = {"P1": 4, "P2": 24, "P3": 72}
TRANSITIONS = {"open": {"in_progress"}, "in_progress": {"resolved"}, "resolved": {"open"}}
CATEGORIES = {"access", "network", "hardware", "security", "application"}
AUDIT = logging.getLogger("vesselops.audit")
if not AUDIT.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    AUDIT.addHandler(handler)
AUDIT.setLevel(logging.INFO)
AUDIT.propagate = False


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat()


def emit(event, **fields):
    # Do not log tokens, request bodies, ticket titles or investigation notes.
    AUDIT.info(
        json.dumps(
            {
                "schema_version": 1,
                "time": stamp(),
                "event": event,
                "request_id": getattr(g, "request_id", None),
                **fields,
            }
        )
    )


def text(data, key, maximum=200, choices=None):
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ValueError(f"{key} must be nonblank text of at most {maximum} characters")
    value = value.strip()
    if choices is not None and value not in choices:
        raise ValueError(f"invalid {key}")
    return value


def json_object(allowed):
    data = request.get_json()
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    extra = set(data) - allowed
    if extra:
        raise ValueError("unexpected fields: " + ", ".join(sorted(extra)))
    return data


def create_app(config=None, store=None):
    app = Flask(__name__)
    app.config.update(
        APP_MODE=os.getenv("APP_MODE", "local"),
        MAX_CONTENT_LENGTH=32 * 1024,
        API_TOKEN=os.getenv("API_TOKEN", ""),
        SQLITE_PATH=os.getenv("SQLITE_PATH", "data/vesselops.db"),
    )
    if config:
        app.config.update(config)
    mode = app.config["APP_MODE"]
    if mode not in ("local", "azure"):
        raise ValueError("APP_MODE must be local or azure")
    if mode == "azure" and store is None:
        from azure.identity import ManagedIdentityCredential
        from azure.keyvault.secrets import SecretClient

        credential = ManagedIdentityCredential()
        vault = SecretClient(vault_url=os.environ["KEY_VAULT_URL"], credential=credential)
        app.config["API_TOKEN"] = vault.get_secret("operator-token").value
        store = CosmosStore(os.environ["COSMOS_ENDPOINT"], credential)
    token = app.config["API_TOKEN"]
    if not isinstance(token, str) or len(token) < 32 or token.startswith("@Microsoft.KeyVault"):
        raise ValueError("provide an API token of at least 32 characters; use tools/local.py")
    app.extensions["store"] = store or SQLiteStore(app.config["SQLITE_PATH"])
    database = app.extensions["store"]

    def authenticated(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            supplied = request.headers.get("Authorization", "")
            if not hmac.compare_digest(supplied.encode(), ("Bearer " + token).encode()):
                emit("auth.failed", route=request.path, method=request.method)
                response = jsonify(error="Unauthorized", request_id=g.request_id)
                response.status_code = 401
                response.headers["WWW-Authenticate"] = 'Bearer realm="VesselOps"'
                return response
            return fn(*args, **kwargs)

        return wrapper

    @app.before_request
    def correlation():
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def secure_headers(response):
        response.headers.update(
            {
                "X-Request-ID": g.request_id,
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "no-referrer",
                "X-Frame-Options": "DENY",
                "Cache-Control": "no-store",
                "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
                "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
            }
        )
        if mode == "azure":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response

    @app.errorhandler(ValueError)
    def validation(exc):
        return jsonify(error=str(exc), request_id=g.request_id), 400

    @app.errorhandler(Missing)
    def missing(_exc):
        return jsonify(error="Record not found", request_id=g.request_id), 404

    @app.errorhandler(Conflict)
    def conflict(_exc):
        return jsonify(error="Record changed. Refresh and try again.", request_id=g.request_id), 409

    @app.errorhandler(Exception)
    def unexpected(exc):
        if isinstance(exc, HTTPException):
            return jsonify(error=exc.name, request_id=g.request_id), exc.code
        emit("app.error", error_type=type(exc).__name__)
        return jsonify(error="Service unavailable", request_id=g.request_id), 503

    @app.get("/")
    def index():
        return render_template("index.html", mode=mode)

    @app.get("/health/live")
    def live():
        return jsonify(status="alive", mode=mode)

    @app.get("/health/ready")
    @authenticated
    def ready():
        database.healthy()
        return jsonify(status="ready", storage="cosmos" if mode == "azure" else "sqlite")

    @app.get("/api/state")
    @authenticated
    def state():
        tickets = database.list("ticket")
        for ticket in tickets:
            ticket["overdue"] = ticket["status"] != "resolved" and datetime.fromisoformat(ticket["due_at"]) < now()
        return jsonify(
            tickets=sorted(tickets, key=lambda x: x["created_at"], reverse=True),
            assets=database.list("asset"),
            incidents=database.list("incident"),
            summary={
                "active": sum(t["status"] != "resolved" for t in tickets),
                "overdue": sum(t["overdue"] for t in tickets),
                "incidents": len(database.list("incident")),
                "mode": mode,
            },
        )

    @app.post("/api/assets")
    @authenticated
    def asset():
        data = json_object({"tag", "hostname", "owner"})
        tag = text(data, "tag", 40)
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", tag):
            raise ValueError("tag may contain letters, digits, underscores and hyphens")
        record = database.create(
            dict(
                id=tag,
                kind="asset",
                hostname=text(data, "hostname", 100),
                owner=text(data, "owner", 100),
                created_at=stamp(),
            )
        )
        emit("asset.created", asset_id=tag)
        return jsonify(record), 201

    @app.post("/api/tickets")
    @authenticated
    def ticket_create():
        data = json_object({"title", "priority", "category", "asset_id"})
        title = text(data, "title", 160)
        priority = text(data, "priority", 2, HOURS)
        category = text(data, "category", 20, CATEGORIES)
        asset_id = data.get("asset_id")
        if asset_id is not None:
            if not isinstance(asset_id, str) or len(asset_id) > 40:
                raise ValueError("invalid asset_id")
            database.get("asset", asset_id)
        created = now()
        record = database.create(
            dict(
                id=str(uuid.uuid4()),
                kind="ticket",
                title=title,
                priority=priority,
                category=category,
                asset_id=asset_id,
                status="open",
                created_at=created.isoformat(),
                due_at=(created + timedelta(hours=HOURS[priority])).isoformat(),
                history=[{"at": created.isoformat(), "status": "open", "note": "Ticket created"}],
            )
        )
        emit("ticket.created", ticket_id=record["id"], priority=priority)
        return jsonify(record), 201

    @app.patch("/api/tickets/<identifier>")
    @authenticated
    def ticket_update(identifier):
        data = json_object({"status", "note", "version"})
        status = text(data, "status", 20, TRANSITIONS)
        note = text(data, "note", 2000)
        version = text(data, "version", 200)
        record = database.get("ticket", identifier)
        if record["version"] != version:
            raise Conflict(identifier)
        if status not in TRANSITIONS[record["status"]]:
            raise ValueError("invalid status transition")
        if len(record["history"]) >= 100:
            raise ValueError("lab history limit reached; open a follow-up ticket")
        record["status"] = status
        record["history"].append({"at": stamp(), "status": status, "note": note})
        updated = database.replace(record, version)
        emit("ticket.changed", ticket_id=identifier, status=status)
        return jsonify(updated)

    @app.post("/api/incidents")
    @authenticated
    def incident_create():
        data = json_object({"title", "severity", "source", "event_ids", "summary"})
        ids = data.get("event_ids")
        if (
            not isinstance(ids, list)
            or not 1 <= len(ids) <= 100
            or any(not isinstance(x, str) or not x or len(x) > 200 for x in ids)
        ):
            raise ValueError("event_ids must contain 1–100 nonblank string IDs")
        record = database.create(
            dict(
                id=str(uuid.uuid4()),
                kind="incident",
                title=text(data, "title", 160),
                severity=text(data, "severity", 10, {"low", "medium", "high"}),
                source=text(data, "source", 40, {"azure", "aws", "synthetic"}),
                event_ids=ids,
                summary=text(data, "summary", 4000),
                created_at=stamp(),
            )
        )
        emit("incident.created", incident_id=record["id"], source=record["source"], severity=record["severity"])
        return jsonify(record), 201

    return app
