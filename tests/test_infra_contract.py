"""Offline security invariants. Provider validation/mocked Terraform tests are separate."""

from pathlib import Path
import hcl2

ROOT = Path(__file__).resolve().parents[1]


def resources():
    result = {}
    for path in (ROOT / "infra").glob("*.tf"):
        with path.open() as file:
            parsed = hcl2.load(file, serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True))
        for resource in parsed.get("resource", []):
            for kind, instances in resource.items():
                for name, config in instances.items():
                    result[(kind, name)] = config
    return result


def test_database_private_identity_only():
    config = resources()[("azurerm_cosmosdb_account", "data")]
    assert config["public_network_access_enabled"] is False
    assert config["local_authentication_disabled"] is True
    assert config["minimal_tls_version"] == "Tls12"


def test_private_endpoint_path_is_wired():
    config = resources()
    app = config[("azurerm_linux_web_app", "app")]
    assert "azurerm_subnet.app.id" in app["virtual_network_subnet_id"]
    endpoint = config[("azurerm_private_endpoint", "cosmos")]
    assert "azurerm_subnet.private.id" in endpoint["subnet_id"]
    assert endpoint["private_service_connection"][0]["subresource_names"] == ["Sql"]
    assert "azurerm_private_dns_zone.cosmos.id" in str(endpoint["private_dns_zone_group"])
    subnet = config[("azurerm_subnet", "private")]
    assert subnet["private_endpoint_network_policies"] == "Enabled"
    assert ("azurerm_subnet_network_security_group_association", "private") in config


def test_app_and_runtime_identity_boundaries():
    config = resources()
    app = config[("azurerm_linux_web_app", "app")]
    assert app["https_only"] is True
    assert app["ftp_publish_basic_authentication_enabled"] is False
    assert app["webdeploy_publish_basic_authentication_enabled"] is False
    assert app["identity"][0]["type"] == "SystemAssigned"
    assert app["site_config"][0]["minimum_tls_version"] == "1.2"
    assert "API_TOKEN" not in app["app_settings"]
    runtime = config[("azurerm_role_assignment", "runtime_vault")]
    assert runtime["role_definition_name"] == "Key Vault Secrets User"
    assert "/secrets/" in runtime["scope"]
    assert not any(
        item.get("role_definition_name") in {"Owner", "Contributor"} and "linux_web_app" in item.get("principal_id", "")
        for item in config.values()
    )


def test_sentinel_opt_in_and_log_destinations():
    config = resources()
    assert "enable_sentinel" in config[("azurerm_sentinel_alert_rule_scheduled", "auth_failures")]["count"]
    app_logs = config[("azurerm_monitor_diagnostic_setting", "app")]
    assert app_logs["log_analytics_destination_type"] == "Dedicated"
    assert {"AppServiceConsoleLogs", "AppServiceHTTPLogs"} == {x["category"] for x in app_logs["enabled_log"]}


def test_sensitive_outputs_are_not_exposed():
    with (ROOT / "infra/outputs.tf").open() as file:
        parsed = hcl2.load(file, serialization_options=hcl2.utils.SerializationOptions(strip_string_quotes=True))
    for output in parsed["output"]:
        for name, config in output.items():
            assert "password" not in name and "token" not in name
            assert "random_password" not in config["value"]
