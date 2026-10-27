output "resource_group" { value = azurerm_resource_group.lab.name }
output "app_name" { value = azurerm_linux_web_app.app.name }
output "app_url" { value = "https://${azurerm_linux_web_app.app.default_hostname}" }
output "vault_name" { value = azurerm_key_vault.app.name }
output "cosmos_name" { value = azurerm_cosmosdb_account.data.name }
output "workspace_id" { value = azurerm_log_analytics_workspace.lab.workspace_id }
