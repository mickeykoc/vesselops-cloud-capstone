"""Audit selected Azure ARM exports or Terraform plan JSON guardrails."""

import argparse
import ipaddress
import json
from pathlib import Path

CRITICAL_TYPES = {"Microsoft.Web/sites", "Microsoft.DocumentDB/databaseAccounts", "Microsoft.KeyVault/vaults"}


def from_plan(plan):
    if not isinstance(plan, dict) or "planned_values" not in plan:
        raise ValueError("not a Terraform plan JSON object")
    result = []

    def visit(module):
        for resource in module.get("resources", []):
            values = resource.get("values", {})
            resource_type = resource.get("type")
            if resource_type == "azurerm_linux_web_app":
                config = (values.get("site_config") or [{}])[0]
                result.append(
                    dict(
                        type="Microsoft.Web/sites",
                        name=resource["address"],
                        identity=(values.get("identity") or [{}])[0],
                        properties={
                            "httpsOnly": values.get("https_only"),
                            "siteConfig": {"minTlsVersion": config.get("minimum_tls_version")},
                        },
                    )
                )
            elif resource_type == "azurerm_cosmosdb_account":
                enabled = values.get("public_network_access_enabled")
                result.append(
                    dict(
                        type="Microsoft.DocumentDB/databaseAccounts",
                        name=resource["address"],
                        properties={
                            "publicNetworkAccess": "Disabled"
                            if enabled is False
                            else "Enabled"
                            if enabled is True
                            else None,
                            "disableLocalAuth": values.get("local_authentication_disabled"),
                        },
                    )
                )
            elif resource_type == "azurerm_key_vault":
                result.append(
                    dict(
                        type="Microsoft.KeyVault/vaults",
                        name=resource["address"],
                        properties={
                            "enableRbacAuthorization": values.get("rbac_authorization_enabled"),
                            "enablePurgeProtection": values.get("purge_protection_enabled"),
                        },
                    )
                )
        for child in module.get("child_modules", []):
            visit(child)

    visit(plan["planned_values"].get("root_module", {}))
    return {"schema": "vesselops.azure-arm.v1", "resources": result}


def audit(inventory):
    if (
        not isinstance(inventory, dict)
        or inventory.get("schema") != "vesselops.azure-arm.v1"
        or not isinstance(inventory.get("resources"), list)
    ):
        raise ValueError("expected vesselops.azure-arm.v1 with resources array")
    findings, seen = [], set()

    def check(ok, rule, resource, description):
        if not ok:
            findings.append({"rule": rule, "resource": resource, "severity": "high", "description": description})

    for item in inventory["resources"]:
        if (
            not isinstance(item, dict)
            or not isinstance(item.get("properties"), dict)
            or not item.get("type")
            or not item.get("name")
        ):
            raise ValueError("resource requires type, name and properties object")
        kind, name, p = item["type"], item["name"], item["properties"]
        seen.add(kind)
        if kind == "Microsoft.Web/sites":
            check(
                p.get("httpsOnly") is True,
                "APP_HTTPS_REQUIRED",
                name,
                "Require HTTPS; missing configuration does not pass.",
            )
            check(
                (p.get("siteConfig") or {}).get("minTlsVersion") in ("1.2", "1.3"),
                "APP_TLS_REQUIRED",
                name,
                "Require minimum TLS 1.2 or 1.3.",
            )
            check(
                "SystemAssigned" in item.get("identity", {}).get("type", ""),
                "APP_MANAGED_IDENTITY",
                name,
                "Require a system-assigned managed identity.",
            )
        elif kind == "Microsoft.DocumentDB/databaseAccounts":
            check(
                p.get("publicNetworkAccess") == "Disabled",
                "DATABASE_PRIVATE",
                name,
                "Disable public database network access.",
            )
            check(
                p.get("disableLocalAuth") is True, "DATABASE_PASSWORDLESS", name, "Disable account-key authentication."
            )
        elif kind == "Microsoft.KeyVault/vaults":
            check(p.get("enableRbacAuthorization") is True, "VAULT_RBAC", name, "Use explicit RBAC authorization.")
            check(
                p.get("enablePurgeProtection") is True,
                "VAULT_PURGE_PROTECTION",
                name,
                "Protect against immediate permanent secret deletion.",
            )
        elif kind == "Microsoft.Network/networkSecurityGroups":
            for rule in p.get("securityRules", []):
                q = rule["properties"]
                if q.get("access") != "Allow" or q.get("direction") != "Inbound":
                    continue
                sources = q.get("sourceAddressPrefixes") or [q.get("sourceAddressPrefix", "")]
                broad = False
                for source in sources:
                    if source in ("*", "Internet"):
                        broad = True
                    else:
                        try:
                            broad |= ipaddress.ip_network(source, strict=False).prefixlen == 0
                        except ValueError:
                            pass
                protocol = q.get("protocol", "").lower()
                ranges = q.get("destinationPortRanges") or [q.get("destinationPortRange", "")]
                admin = False
                if protocol in ("*", "tcp"):
                    for value in ranges:
                        if value == "*":
                            admin = True
                        elif value:
                            start, _, end = value.partition("-")
                            admin |= any(int(start) <= port <= int(end or start) for port in (22, 3389))
                check(
                    not (broad and admin),
                    "NSG_ADMIN_WORLD",
                    name,
                    "Internet-wide SSH/RDP ingress requires restriction. Rule alone does not prove reachability.",
                )
    for missing in sorted(CRITICAL_TYPES - seen):
        check(
            False, "MISSING_COVERAGE", missing, "Required resource type absent; cannot certify this project inventory."
        )
    return {
        "scope": "selected explicit configuration guardrails; not complete security or reachability assessment",
        "resources_checked": len(inventory["resources"]),
        "findings": findings,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--terraform-plan", action="store_true")
    parser.add_argument("--fail-on-high", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        inventory = json.loads(args.input.read_text())
        if args.terraform_plan:
            inventory = from_plan(inventory)
        result = audit(inventory)
        rendered = json.dumps(result, indent=2)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n")
        print(rendered)
        return int(args.fail_on_high and bool(result["findings"]))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Input error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
