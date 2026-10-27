"""Analyze exported AppServiceConsoleLogs; accepts CLI rows or REST tables."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path


def rows(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict) or not isinstance(payload.get("tables"), list):
        raise ValueError("expected Azure CLI row array or Log Analytics tables response")
    result = []
    for table in payload["tables"]:
        columns = [column["name"] for column in table["columns"]]
        result.extend(dict(zip(columns, row, strict=True)) for row in table["rows"])
    return result


def analyze(payload, threshold=5):
    if threshold < 1:
        raise ValueError("threshold must be positive")
    groups = defaultdict(list)
    invalid = []
    seen = set()
    for index, row in enumerate(rows(payload)):
        try:
            event = json.loads(row["ResultDescription"])
            if not isinstance(event, dict):
                raise ValueError("log JSON must be an object")
            if event.get("event") != "auth.failed":
                continue
            identifier = event["request_id"]
            if not isinstance(identifier, str) or not identifier:
                raise ValueError("request_id must be nonblank text")
            dt = datetime.fromisoformat(row["TimeGenerated"].replace("Z", "+00:00"))
            if dt.tzinfo is None:
                raise ValueError("timestamp must contain timezone")
            resource = row["_ResourceId"]
            if not isinstance(resource, str) or not resource:
                raise ValueError("resource ID must be present")
            identity = (resource.lower(), identifier)
            if identity in seen:
                continue
            seen.add(identity)
            bucket = int(dt.timestamp()) // 300
            groups[(resource.lower(), bucket)].append(identifier)
        except (KeyError, ValueError, TypeError) as exc:
            invalid.append({"row": index, "reason": str(exc)})
    alerts = [
        {
            "rule": "OPERATOR_AUTH_FAILURE_CLUSTER",
            "severity": "medium",
            "resource": resource,
            "window_start": datetime.fromtimestamp(bucket * 300, tz=timezone.utc).isoformat(),
            "event_ids": ids,
            "count": len(ids),
            "reason": "Repeated rejected operator authentication; verify operator mistakes before escalating.",
        }
        for (resource, bucket), ids in sorted(groups.items())
        if len(ids) >= threshold
    ]
    return {"scope": "exported console rows; fixed UTC five-minute buckets", "alerts": alerts, "invalid_rows": invalid}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        report = analyze(json.loads(args.input.read_text()))
        rendered = json.dumps(report, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n")
        print(rendered)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Input error: {exc}\n")


if __name__ == "__main__":
    main()
