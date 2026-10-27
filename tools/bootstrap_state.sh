#!/usr/bin/env bash
# Run once as your interactive Azure user. Uses Entra auth, never storage keys.
set -euo pipefail
if [ "$#" -ne 2 ]; then echo 'Usage: bash tools/bootstrap_state.sh SUBSCRIPTION_UUID REGION'; exit 2; fi
subscription="$1"
region="$2"
az account set --subscription "$subscription"
state_rg="rg-vesselops-state"
suffix="$(python3 -c 'import secrets; print(secrets.token_hex(4))')"
account="stvesselops${suffix}"
user_id="$(az ad signed-in-user show --query id -o tsv)"
for namespace in Microsoft.ManagedIdentity Microsoft.Web Microsoft.Network Microsoft.DocumentDB Microsoft.KeyVault Microsoft.OperationalInsights Microsoft.Insights Microsoft.SecurityInsights Microsoft.Consumption; do
  az provider register --namespace "$namespace" --wait --only-show-errors
done
az group create --name "$state_rg" --location "$region" --output none
az storage account create --resource-group "$state_rg" --name "$account" --location "$region" \
  --sku Standard_LRS --kind StorageV2 --https-only true --min-tls-version TLS1_2 \
  --allow-shared-key-access false --allow-blob-public-access false --output none
scope="/subscriptions/$subscription/resourceGroups/$state_rg/providers/Microsoft.Storage/storageAccounts/$account"
az role assignment create --assignee-object-id "$user_id" --assignee-principal-type User \
  --scope "$scope" --role 'Storage Blob Data Contributor' --output none
az storage account blob-service-properties update --account-name "$account" --resource-group "$state_rg" \
  --enable-versioning true --enable-delete-retention true --delete-retention-days 7 --output none
created=false
for attempt in {1..24}; do
  if az storage container create --account-name "$account" --name tfstate --auth-mode login --output none --only-show-errors; then created=true; break; fi
  sleep 5
done
if [ "$created" != true ]; then echo 'State container creation failed. RBAC may still be propagating. Reuse the created account; do not rerun the whole script.'; exit 1; fi
mkdir -p infra
cat > infra/backend.hcl <<EOF
resource_group_name  = "$state_rg"
storage_account_name = "$account"
container_name       = "tfstate"
key                  = "vesselops.tfstate"
use_azuread_auth     = true
EOF
printf 'State backend ready. Group: %s Account: %s\nNext: terraform -chdir=infra init -backend-config=backend.hcl\n' "$state_rg" "$account"
