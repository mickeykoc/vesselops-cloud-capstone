resource "azurerm_log_analytics_workspace" "lab" {
  name                = "log-vesselops-${local.suffix}"
  location            = var.location
  resource_group_name = azurerm_resource_group.lab.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  daily_quota_gb      = 0.1
  tags                = local.tags
}
resource "azurerm_monitor_diagnostic_setting" "app" {
  name                           = "app-to-workspace"
  target_resource_id             = azurerm_linux_web_app.app.id
  log_analytics_workspace_id     = azurerm_log_analytics_workspace.lab.id
  log_analytics_destination_type = "Dedicated"
  enabled_log { category = "AppServiceConsoleLogs" }
  enabled_log { category = "AppServiceHTTPLogs" }
}
resource "azurerm_monitor_diagnostic_setting" "vault" {
  name                       = "vault-to-workspace"
  target_resource_id         = azurerm_key_vault.app.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.lab.id
  enabled_log { category = "AuditEvent" }
}
resource "azurerm_monitor_diagnostic_setting" "cosmos" {
  name                           = "cosmos-to-workspace"
  target_resource_id             = azurerm_cosmosdb_account.data.id
  log_analytics_workspace_id     = azurerm_log_analytics_workspace.lab.id
  log_analytics_destination_type = "Dedicated"
  enabled_log { category = "DataPlaneRequests" }
}
resource "azurerm_sentinel_log_analytics_workspace_onboarding" "lab" {
  count                        = var.enable_sentinel ? 1 : 0
  workspace_id                 = azurerm_log_analytics_workspace.lab.id
  customer_managed_key_enabled = false
}
resource "azurerm_sentinel_alert_rule_scheduled" "auth_failures" {
  count                      = var.enable_sentinel ? 1 : 0
  name                       = "vesselops-auth-failures"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.lab.id
  display_name               = "VesselOps repeated failed operator authentication"
  description                = "Five rejected API calls in five minutes on one app resource. Investigate; not proof of compromise."
  severity                   = "Medium"
  enabled                    = true
  query                      = file("${path.module}/../detections/auth_failures.kql")
  query_frequency            = "PT5M"
  query_period               = "PT10M"
  trigger_operator           = "GreaterThan"
  trigger_threshold          = 0
  tactics                    = ["CredentialAccess"]
  depends_on                 = [azurerm_sentinel_log_analytics_workspace_onboarding.lab]
}
resource "azurerm_sentinel_alert_rule_scheduled" "vault_denied" {
  count                      = var.enable_sentinel ? 1 : 0
  name                       = "vesselops-vault-denied"
  log_analytics_workspace_id = azurerm_log_analytics_workspace.lab.id
  display_name               = "VesselOps denied secret access"
  description                = "Failed Key Vault SecretGet operations. Check identity scope and expected startup behavior."
  severity                   = "Medium"
  enabled                    = true
  query                      = file("${path.module}/../detections/vault_denied.kql")
  query_frequency            = "PT5M"
  query_period               = "PT10M"
  trigger_operator           = "GreaterThan"
  trigger_threshold          = 0
  tactics                    = ["CredentialAccess"]
  depends_on                 = [azurerm_sentinel_log_analytics_workspace_onboarding.lab]
}
