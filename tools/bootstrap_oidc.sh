#!/usr/bin/env bash
# Run after the first interactive Terraform apply. Scopes roles to lab/state only.
set -euo pipefail
if [ "$#" -ne 4 ]; then echo 'Usage: bash tools/bootstrap_oidc.sh OWNER/REPO STATE_RG STATE_ACCOUNT SUBSCRIPTION_UUID'; exit 2; fi
repository="$1"; state_rg="$2"; state_account="$3"; subscription="$4"
if [[ ! "$repository" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]; then echo 'Expected owner/repository'; exit 2; fi
az account set --subscription "$subscription"
lab_rg="$(terraform -chdir=infra output -raw resource_group)"
identity_name="id-vesselops-github"
az identity create --resource-group "$state_rg" --name "$identity_name" --output none
principal="$(az identity show --resource-group "$state_rg" --name "$identity_name" --query principalId -o tsv)"
client="$(az identity show --resource-group "$state_rg" --name "$identity_name" --query clientId -o tsv)"
tenant="$(az account show --query tenantId -o tsv)"
az identity federated-credential create --resource-group "$state_rg" --identity-name "$identity_name" \
  --name github-lab --issuer 'https://token.actions.githubusercontent.com' \
  --subject "repo:$repository:environment:vesselops-lab" --audiences api://AzureADTokenExchange --output none
lab_scope="/subscriptions/$subscription/resourceGroups/$lab_rg"
for role in Contributor 'Role Based Access Control Administrator'; do
  az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
    --role "$role" --scope "$lab_scope" --output none
done
state_scope="/subscriptions/$subscription/resourceGroups/$state_rg/providers/Microsoft.Storage/storageAccounts/$state_account"
az role assignment create --assignee-object-id "$principal" --assignee-principal-type ServicePrincipal \
  --role 'Storage Blob Data Contributor' --scope "$state_scope" --output none
# Preserve the human operator's secret read permission after Terraform switches its
# deployer_vault assignment to the workflow identity on subsequent applies.
operator="$(az ad signed-in-user show --query id -o tsv)"
vault="$(terraform -chdir=infra output -raw vault_name)"
vault_scope="$lab_scope/providers/Microsoft.KeyVault/vaults/$vault"
az role assignment create --assignee-object-id "$operator" --assignee-principal-type User \
  --role 'Key Vault Secrets User' --scope "$vault_scope" --output none
printf '\nConfigure GitHub environment vesselops-lab with main-only deployment and required reviewer if your plan supports it.\n'
printf 'Environment variables:\nAZURE_CLIENT_ID=%s\nAZURE_TENANT_ID=%s\nAZURE_SUBSCRIPTION_ID=%s\nTF_STATE_RG=%s\nTF_STATE_ACCOUNT=%s\n' "$client" "$tenant" "$subscription" "$state_rg" "$state_account"
printf '\nSet BUDGET_EMAIL as an environment secret. No Azure client secret is needed.\n'
