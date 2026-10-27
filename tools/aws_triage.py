"""Offline CloudTrail triage: candidate alerts require analyst investigation."""

import argparse
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json
from pathlib import Path


def timestamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("eventTime must include a timezone")
    return dt


def analyze(records, threshold=5, window_minutes=10):
    if threshold < 1 or window_minutes < 1:
        raise ValueError("threshold and window must be positive")
    valid, errors, alerts, seen = [], [], [], set()
    for index, event in enumerate(records):
        try:
            if not isinstance(event, dict):
                raise ValueError("event must be an object")
            for key in ("eventTime", "eventName", "eventSource", "eventID"):
                if not isinstance(event.get(key), str) or not event[key]:
                    raise ValueError("missing or invalid " + key)
            dt = timestamp(event["eventTime"])
            if not isinstance(event.get("userIdentity", {}), dict):
                raise ValueError("userIdentity must be an object")
            if not isinstance(event.get("responseElements") or {}, dict):
                raise ValueError("responseElements must be an object or null")
            if event["eventID"] in seen:
                continue
            seen.add(event["eventID"])
            valid.append((dt, event))
        except (ValueError, TypeError) as exc:
            errors.append({"index": index, "error": str(exc)})
    failures = defaultdict(deque)
    for dt, event in sorted(valid, key=lambda item: item[0]):
        identity = event.get("userIdentity", {})
        actor = identity.get("arn") or identity.get("principalId") or "unknown"
        ip = event.get("sourceIPAddress") or "unknown"
        evidence = {"event_id": event["eventID"], "time": event["eventTime"], "actor": actor, "source": ip}

        def alert(rule, severity, reason, ids=None):
            alerts.append(
                dict(evidence, rule=rule, severity=severity, reason=reason, related_event_ids=ids or [event["eventID"]])
            )

        name, source = event["eventName"], event["eventSource"]
        # Failed API requests are not successful configuration changes.
        if identity.get("type") == "Root" and not identity.get("invokedBy"):
            alert("ROOT_ACTIVITY", "high", "Review root principal activity and approved change history.")
        if (
            source == "cloudtrail.amazonaws.com"
            and name in ("StopLogging", "DeleteTrail")
            and not event.get("errorCode")
        ):
            alert("LOGGING_CHANGE", "high", "Successful logging change; validate approval and trail coverage.")
        if source == "signin.amazonaws.com" and name == "ConsoleLogin":
            result = (event.get("responseElements") or {}).get("ConsoleLogin")
            key = (actor, ip)
            queue = failures[key]
            while queue and dt - queue[0][0] > timedelta(minutes=window_minutes):
                queue.popleft()
            if result == "Failure":
                queue.append((dt, event["eventID"]))
                # One threshold alert per continuous cluster; later success is correlated separately.
                if len(queue) == threshold:
                    alert(
                        "LOGIN_FAILURE_CLUSTER",
                        "medium",
                        f"{threshold} failures within {window_minutes} minutes.",
                        [x[1] for x in queue],
                    )
            elif result == "Success":
                if len(queue) >= threshold:
                    alert(
                        "SUCCESS_AFTER_FAILURES",
                        "high",
                        "Successful login after repeated failures; verify with account owner.",
                        [x[1] for x in queue] + [event["eventID"]],
                    )
                queue.clear()
    return {"input_events": len(records), "unique_valid_events": len(valid), "invalid_events": errors, "alerts": alerts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--threshold", type=int, default=5)
    args = parser.parse_args()
    try:
        payload = json.loads(args.input.read_text())
        records = payload.get("Records") if isinstance(payload, dict) else payload
        if not isinstance(records, list):
            raise ValueError("expected a JSON array or CloudTrail Records array")
        report = analyze(records, args.threshold)
        rendered = json.dumps(report, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n")
        print(rendered)
    except (OSError, ValueError, TypeError) as exc:
        parser.exit(2, f"Input error: {exc}\n")


if __name__ == "__main__":
    main()
