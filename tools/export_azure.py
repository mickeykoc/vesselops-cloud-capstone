"""Read-only Azure CLI collector. Export only selected nonsecret ARM fields."""

import argparse
import json
from pathlib import Path
import subprocess


def az(*args):
    return json.loads(subprocess.check_output(["az", *args, "--output", "json", "--only-show-errors"], text=True))


def export(group):
    resources = []
    for item in az("resource", "list", "--resource-group", group):
        kind = item["type"]
        if kind not in {
            "Microsoft.Web/sites",
            "Microsoft.DocumentDB/databaseAccounts",
            "Microsoft.KeyVault/vaults",
            "Microsoft.Network/networkSecurityGroups",
        }:
            continue
        raw = az("resource", "show", "--ids", item["id"])
        p = raw.get("properties", {})
        if kind == "Microsoft.Web/sites":
            config = az("webapp", "config", "show", "--resource-group", group, "--name", item["name"])
            properties = {"httpsOnly": p.get("httpsOnly"), "siteConfig": {"minTlsVersion": config.get("minTlsVersion")}}
        elif kind == "Microsoft.DocumentDB/databaseAccounts":
            properties = {key: p.get(key) for key in ("publicNetworkAccess", "disableLocalAuth")}
        elif kind == "Microsoft.KeyVault/vaults":
            properties = {key: p.get(key) for key in ("enableRbacAuthorization", "enablePurgeProtection")}
        else:
            properties = {"securityRules": p.get("securityRules", [])}
        record = dict(name=item["name"], type=kind, properties=properties)
        if kind == "Microsoft.Web/sites":
            record["identity"] = {"type": raw.get("identity", {}).get("type")}
        resources.append(record)
    return {"schema": "vesselops.azure-arm.v1", "resources": resources}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resource-group", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = export(args.resource_group)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {len(result['resources'])} selected resource configurations. Review identifiers before publishing.")
