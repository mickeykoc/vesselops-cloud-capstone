# Azure deployment and cleanup

## Status and requirements

Cloud execution has not occurred in this delivery. This runbook and automation are supplied for the first real run. You need an Azure subscription you control, Azure CLI, Terraform 1.11.4, Python 3.12, and a GitHub repository if using Actions. Subscription/tenant policies, region capacity and Azure provider permissions can affect deployment. Use Bash (WSL on Windows is suitable for these shell scripts).

The first interactive operator must be allowed to register providers and create the lab/state resource groups, assign scoped RBAC roles, configure budgets and create resources. Do not grant the eventual workflow subscription Owner. After initial setup, its roles are scoped to the dedicated lab resource group and state account.

## 1. Review cost and resource lifecycle

This deploys paid resources: Linux App Service B1, Cosmos DB serverless, a private endpoint, Key Vault and Log Analytics. Sentinel is opt-in. Use the Azure pricing calculator for your selected region before applying: https://azure.microsoft.com/pricing/calculator/

The resource-group budget sends alerts; it does not stop spending. The workspace ingestion quota is not an immediate hard cost cap and does not cover every service charge. The state storage account is separate and excluded from the lab budget. Keep a cost record and destroy the lab after collecting evidence. Keep the backend until you have confirmed all tracked resources are removed.

## 2. Bootstrap protected Terraform state

```sh
az login
bash tools/bootstrap_state.sh YOUR_SUBSCRIPTION_UUID eastus2
```

The script creates a dedicated state storage account, disables shared-key and anonymous blob access, enables versioning/soft delete and grants your signed-in user Blob Data Contributor there. Its authenticated public endpoint permits GitHub-hosted runners. The generated `infra/backend.hcl` has identifiers only and is ignored by Git.

Run this script once. If interrupted after creating resources, reuse the existing account and finish the failed command; rerunning creates another account. The script assumes interactive user login, not a service-principal session.

Terraform state and plan files contain the generated operator token. Treat access to them as secret access even though outputs do not print it. Do not commit/upload state or plan JSON. Local `.terraform/` caches may also contain backend configuration.

## 3. First interactive infrastructure deployment

```sh
cp infra/terraform.tfvars.example infra/terraform.tfvars
```

Edit subscription, email, location and the first day of the current month. Keep Sentinel false initially so the log tables can be populated before rule creation. Then:

```sh
terraform -chdir=infra init -backend-config=backend.hcl
terraform -chdir=infra validate
terraform -chdir=infra plan -out=lab.tfplan
terraform -chdir=infra show -json lab.tfplan > /tmp/vesselops-plan.json
python tools/azure_audit.py /tmp/vesselops-plan.json --terraform-plan --fail-on-high
terraform -chdir=infra apply lab.tfplan
rm /tmp/vesselops-plan.json infra/lab.tfplan
```

Review the plan before applying. The custom policy checks explicit HTTPS/TLS, managed identity, private database access, disabled DB keys and vault protections. It is deliberately limited, not a compliance certification. A failed check or missing coverage must be investigated. Use one selected region; do not create duplicate stacks to troubleshoot a transient issue.

RBAC propagation can cause a transient Key Vault secret creation 403 on the first apply. Verify that the deployer role exists, allow it to propagate, and re-plan/apply using the same backend. Do not open permissions broadly to bypass the issue.

## 4. Package and deploy the application

```sh
python tools/package_app.py --output /tmp/vesselops-app.zip
APP_NAME="$(terraform -chdir=infra output -raw app_name)"
LAB_RG="$(terraform -chdir=infra output -raw resource_group)"
az webapp deploy --resource-group "$LAB_RG" --name "$APP_NAME" --src-path /tmp/vesselops-app.zip --type zip
az webapp restart --resource-group "$LAB_RG" --name "$APP_NAME"
```

Python remote build is enabled. The package contains only app code, WSGI and runtime requirements. Basic publishing authentication is disabled. Identity-based deployment support depends on your current Azure CLI; use the OIDC workflow below if interactive ZIP deployment is unavailable. The app reads one Key Vault secret at process startup, then connects to Cosmos with its managed identity. Role assignment propagation can require a later restart. The first build may take several minutes.

Get your operator token into your own shell without echoing it into a transcript:

```sh
VAULT_NAME="$(terraform -chdir=infra output -raw vault_name)"
export API_TOKEN="$(az keyvault secret show --vault-name "$VAULT_NAME" --name operator-token --query value -o tsv)"
```

Open the app URL (`terraform -chdir=infra output -raw app_url`) and paste the token using your local clipboard. Do not save it to evidence. `curl /health/live` is only liveness; use the authenticated scenario to establish data readiness:

```sh
python tools/scenario.py --base-url "$(terraform -chdir=infra output -raw app_url)" --output evidence/my_cloud_scenario.json
```

## 5. Verify identity and private connectivity

- Confirm `publicNetworkAccess=Disabled` and `disableLocalAuth=true` on the Cosmos resource.
- In App Service SSH, resolve your Cosmos hostname. It should resolve through the private DNS configuration to private endpoint addresses. Record the result, excluding credentials.
- Confirm `/health/ready` with your bearer token returns `storage=cosmos`. The endpoint exercises container metadata access through the configured credential and network path.
- Attempt direct database access outside the VNet with an otherwise authorized test identity. Record expected denial. Do not weaken the firewall to make a screenshot.
- Verify the app identity's Cosmos data role is limited to this dedicated account, and its vault read role to the operator-token secret.
- Collect before/after configuration exports using the supplied read-only collector. A configuration export alone does not prove network reachability.

```sh
python tools/export_azure.py --resource-group "$LAB_RG" --output evidence/my_azure_inventory.json
python tools/azure_audit.py evidence/my_azure_inventory.json --fail-on-high --output evidence/my_azure_audit.json
```

## 6. Configure GitHub OIDC deployment

Publish this source to your own GitHub repository first. The source and validation workflow are published at mickeykoc/vesselops-cloud-capstone. Ensure `main` is protected and PR tests must pass. Run the OIDC helper after the first apply, passing the state identifiers printed by bootstrap:

```sh
bash tools/bootstrap_oidc.sh OWNER/REPO STATE_RESOURCE_GROUP STATE_ACCOUNT YOUR_SUBSCRIPTION_UUID
```

Create GitHub environment `vesselops-lab`; restrict deployments to `main`, and configure a required reviewer if supported by your GitHub plan. Add the environment variables printed by the helper, `AZURE_LOCATION`, and optional `ENABLE_SENTINEL=false`. Add environment secret `BUDGET_EMAIL`. These Azure identifiers are not passwords. The identity trusts only the matching repository/environment OIDC subject. No client secret or publish profile is stored.

The helper grants Contributor plus Role Based Access Control Administrator **only on the lab resource group**, and Blob Data Contributor on the dedicated state account. This infrastructure identity has broad lab control, including role assignment capability; that is an explicit lab tradeoff. The runtime identity has no such control-plane roles. After deleting the entire lab group, its scoped workflow roles are gone; recreation must start with the interactive operator again.

The helper also preserves a human secret-read role, since the Terraform deployer-vault assignment changes to the workflow principal on its first apply. Initial role propagation may require retrying the workflow later. Do not add subscription-wide Owner to solve it.

Run **Deploy lab or destroy lab**, operation `deploy`, confirmation `DEPLOY-LAB`. The workflow tests, audits dependencies, plans, checks plan guardrails, applies that plan, builds the allowlisted ZIP and deploys it. Public liveness does not establish database health; run the authenticated scenario afterward. It is manual to prevent each commit from creating paid resources.

## 7. Export logs and enable optional Sentinel

After the scenario, verify that `AppServiceConsoleLogs` and Key Vault `AzureDiagnostics` have ingested rows. Install the Azure CLI `log-analytics` extension if requested. Using the workspace GUID from Terraform:

```sh
az monitor log-analytics query --workspace YOUR_WORKSPACE_GUID --analytics-query 'AppServiceConsoleLogs | where TimeGenerated > ago(1h) | project TimeGenerated, _ResourceId, ResultDescription' --output json > evidence/my_console_export.json
python tools/azure_triage.py evidence/my_console_export.json --output evidence/my_triage.json
```

Sanitize resource identifiers before publishing. The analyzer accepts the CLI row array and the REST `tables` response. It deduplicates request IDs; KQL counts raw ingested rows, so duplicate ingestion can cause different counts. It uses fixed five-minute buckets, not a sliding interval. Boundaries can split a cluster; this is a documented detection limitation.

When tables exist, set `enable_sentinel=true` in local variables or GitHub environment variable `ENABLE_SENTINEL=true` and apply again. KQL has not been executed against a live workspace in this delivery. Inspect actual table schemas/ingestion and validate queries first. Optional Sentinel creation may fail on query schema validation until the tables exist. Queries overlap lookback windows, so repeat alerts are possible. Neither rule asserts that a compromise occurred.

The project deliberately avoids exposing a honeypot. It generates a controlled incident with known ground truth instead. No claim of observing real attackers is appropriate.

## 8. Rollback, rotation and teardown

Application rollback: deploy the package from a known good source commit. No database schema migration is required for this document format. Record the commit you deployed; GitHub OIDC does not by itself prove the source is safe.

Operator token rotation: `terraform -chdir=infra apply -replace=random_password.operator`, review the replacement plan, then restart the web app. All workers cache the token at startup, so a restart is required. Remove the old token from local shells and browser sessions.

```sh
terraform -chdir=infra plan -destroy
terraform -chdir=infra destroy
```

Or dispatch workflow operation `destroy`, confirmation `DESTROY-LAB`. Do not delete the resource group manually while Terraform still tracks it. Verify the lab group and private endpoint are gone in Azure, review costs, and retain sanitized evidence. Purge-protected Key Vault stays soft-deleted for its retention period; do not disable protection to reuse the name immediately. The separate state account/identity remain intentionally. Delete that dedicated backend group only after verifying no remaining resources depend on the state and accepting the loss of recovery history.
