import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from tools.azure_audit import audit, from_plan
from tools.azure_triage import analyze, rows
from tools.aws_triage import analyze as aws_analyze
from tools.package_app import package
from tools.scenario import execute

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "fixtures" / name).read_text())


def test_before_after_security_policy():
    assert len(audit(fixture("azure_insecure.json"))["findings"]) == 3
    assert audit(fixture("azure_secure.json"))["findings"] == []


def test_missing_resources_are_failures():
    report = audit({"schema": "vesselops.azure-arm.v1", "resources": []})
    assert len(report["findings"]) == 3


def test_unknown_boolean_does_not_pass():
    data = fixture("azure_secure.json")
    data["resources"][1]["properties"]["disableLocalAuth"] = None
    assert audit(data)["findings"][0]["rule"] == "DATABASE_PASSWORDLESS"


@pytest.mark.parametrize("source", ["::/0", "0.0.0.0/0", "*", "Internet"])
def test_world_admin_variants(source):
    data = fixture("azure_secure.json")
    rule = data["resources"][-1]["properties"]["securityRules"][0]["properties"]
    rule.update(sourceAddressPrefix=source, destinationPortRange="3389")
    assert audit(data)["findings"][0]["rule"] == "NSG_ADMIN_WORLD"


def test_plan_adapter_traverses_modules_and_unknowns_fail():
    plan = {
        "planned_values": {
            "root_module": {
                "child_modules": [
                    {
                        "resources": [
                            {
                                "type": "azurerm_cosmosdb_account",
                                "address": "module.data.db",
                                "values": {
                                    "public_network_access_enabled": False,
                                    "local_authentication_disabled": True,
                                },
                            }
                        ]
                    }
                ]
            }
        }
    }
    exported = from_plan(plan)
    assert exported["resources"][0]["properties"]["publicNetworkAccess"] == "Disabled"
    assert all(f["rule"] == "MISSING_COVERAGE" for f in audit(exported)["findings"])
    with pytest.raises(ValueError):
        from_plan({})


def test_azure_threshold_and_deduplication():
    data = fixture("azure_console.json")
    assert len(analyze(data)["alerts"]) == 1
    assert analyze(data[:4])["alerts"] == []
    assert analyze([data[0]] * 10)["alerts"] == []


def test_azure_buckets_and_timezone():
    data = fixture("azure_console.json")
    data[-1]["TimeGenerated"] = "2026-10-27T14:06:00Z"
    assert analyze(data)["alerts"] == []
    data[-1]["TimeGenerated"] = "2026-10-27T14:01:05"
    assert len(analyze(data)["invalid_rows"]) == 1


def test_azure_rest_shape_and_malformed_rows():
    source = fixture("azure_console.json")
    columns = list(source[0])
    result = rows(
        {"tables": [{"columns": [{"name": key} for key in columns], "rows": [list(item.values()) for item in source]}]}
    )
    assert result == source
    assert len(analyze([{"ResultDescription": "not json"}])["invalid_rows"]) == 1
    with pytest.raises(ValueError):
        rows({"bad": True})


def test_aws_real_export_wrapper():
    data = fixture("aws_cloudtrail.json")
    report = aws_analyze(data["Records"])
    assert len(report["alerts"]) == 4
    assert report["unique_valid_events"] == 7


def test_deploy_package_excludes_sensitive_paths(tmp_path):
    output = package(tmp_path / "deploy.zip")
    with zipfile.ZipFile(output) as archive:
        names = archive.namelist()
        assert "wsgi.py" in names and "requirements.txt" in names
        assert all(name.startswith("app/") or name in ("wsgi.py", "requirements.txt") for name in names)
        assert not any("evidence" in name or ".db" in name or ".tfstate" in name for name in names)
        assert archive.testzip() is None


def test_policy_cli_exit_codes(tmp_path):
    script = ROOT / "tools/azure_audit.py"
    assert (
        subprocess.run(
            [sys.executable, script, ROOT / "fixtures/azure_insecure.json", "--fail-on-high"], capture_output=True
        ).returncode
        == 1
    )
    assert (
        subprocess.run(
            [sys.executable, script, ROOT / "fixtures/azure_secure.json", "--fail-on-high"], capture_output=True
        ).returncode
        == 0
    )
    invalid = tmp_path / "invalid.json"
    invalid.write_text("{}")
    assert subprocess.run([sys.executable, script, invalid], capture_output=True).returncode == 2


def test_scenario_rejects_insecure_remote_url():
    with pytest.raises(ValueError):
        execute("http://example.com", "x" * 48)
    with pytest.raises(ValueError):
        execute("https://user:password@example.com", "x" * 48)


def test_controlled_scenario_over_local_http(tmp_path):
    import secrets
    import threading
    from werkzeug.serving import make_server
    from app import create_app

    token = secrets.token_urlsafe(36)
    app = create_app({"API_TOKEN": token, "APP_MODE": "local", "SQLITE_PATH": str(tmp_path / "scenario.db")})
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = execute("http://127.0.0.1:" + str(server.server_port), token)
        assert result["expected_rejections"] == 5
        assert len(set(result["request_ids"])) == 5
        assert result["ticket_status"] == "resolved"
        assert result["storage"] == "sqlite"
    finally:
        server.shutdown()
        thread.join(timeout=5)
