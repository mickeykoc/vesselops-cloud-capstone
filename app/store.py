"""Document persistence with optimistic concurrency in SQLite and Cosmos DB."""

from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3


class Conflict(Exception):
    pass


class Missing(Exception):
    pass


class SQLiteStore:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute(
                "CREATE TABLE IF NOT EXISTS documents (id TEXT PRIMARY KEY, kind TEXT NOT NULL, body TEXT NOT NULL, version INTEGER NOT NULL)"
            )

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self, kind):
        with self.connect() as db:
            rows = db.execute("SELECT body,version FROM documents WHERE kind=? ORDER BY id", (kind,)).fetchall()
        return [dict(json.loads(row["body"]), version=str(row["version"])) for row in rows]

    def get(self, kind, identifier):
        with self.connect() as db:
            row = db.execute("SELECT body,version FROM documents WHERE kind=? AND id=?", (kind, identifier)).fetchone()
        if row is None:
            raise Missing(identifier)
        return dict(json.loads(row["body"]), version=str(row["version"]))

    def create(self, document):
        body = {key: value for key, value in document.items() if key != "version"}
        try:
            with self.connect() as db:
                db.execute("INSERT INTO documents VALUES(?,?,?,1)", (body["id"], body["kind"], json.dumps(body)))
        except sqlite3.IntegrityError as exc:
            raise Conflict(document["id"]) from exc
        return dict(body, version="1")

    def replace(self, document, version):
        body = {key: value for key, value in document.items() if key != "version"}
        with self.connect() as db:
            cursor = db.execute(
                "UPDATE documents SET body=?,version=version+1 WHERE id=? AND kind=? AND version=?",
                (json.dumps(body), body["id"], body["kind"], int(version)),
            )
            if cursor.rowcount != 1:
                raise Conflict(body["id"])
        return dict(body, version=str(int(version) + 1))

    def healthy(self):
        with self.connect() as db:
            db.execute("SELECT 1").fetchone()
        return True


class CosmosStore:
    """One dedicated account/container; /kind partition, ETag-protected updates."""

    def __init__(self, endpoint, credential, database="vesselops", container="records"):
        from azure.cosmos import CosmosClient

        self.client = CosmosClient(endpoint, credential=credential)
        self.container = self.client.get_database_client(database).get_container_client(container)

    @staticmethod
    def clean(document):
        return {
            **{key: value for key, value in document.items() if not key.startswith("_")},
            "version": document["_etag"],
        }

    def list(self, kind):
        items = self.container.query_items(
            query="SELECT * FROM c WHERE c.kind = @kind",
            parameters=[{"name": "@kind", "value": kind}],
            partition_key=kind,
        )
        return [self.clean(document) for document in items]

    def get(self, kind, identifier):
        from azure.cosmos.exceptions import CosmosResourceNotFoundError

        try:
            return self.clean(self.container.read_item(item=identifier, partition_key=kind))
        except CosmosResourceNotFoundError as exc:
            raise Missing(identifier) from exc

    def create(self, document):
        from azure.cosmos.exceptions import CosmosResourceExistsError

        body = {key: value for key, value in document.items() if key != "version"}
        try:
            return self.clean(self.container.create_item(body=body))
        except CosmosResourceExistsError as exc:
            raise Conflict(document["id"]) from exc

    def replace(self, document, version):
        from azure.core import MatchConditions
        from azure.cosmos.exceptions import CosmosHttpResponseError

        body = {key: value for key, value in document.items() if key != "version"}
        try:
            return self.clean(
                self.container.replace_item(
                    item=body["id"], body=body, etag=version, match_condition=MatchConditions.IfNotModified
                )
            )
        except CosmosHttpResponseError as exc:
            if exc.status_code in (404, 409, 412):
                raise Conflict(body["id"]) from exc
            raise

    def healthy(self):
        self.container.read()
        return True
