mock_provider "azurerm" {
  mock_data "azurerm_client_config" {
    defaults = {
      tenant_id = "11111111-1111-1111-1111-111111111111"
      object_id = "22222222-2222-2222-2222-222222222222"
    }
  }
}
mock_provider "random" {
  mock_resource "random_string" { defaults = { result = "lab12345" } }
}
variables {
  subscription_id   = "00000000-0000-0000-0000-000000000000"
  budget_email      = "lab@example.com"
  budget_start_date = "2026-10-01T00:00:00Z"
}
run "private_passwordless_data" {
  command = plan
  assert {
    condition     = azurerm_cosmosdb_account.data.public_network_access_enabled == false
    error_message = "Database public network access must remain disabled."
  }
  assert {
    condition     = azurerm_cosmosdb_account.data.local_authentication_disabled == true
    error_message = "Database account-key authentication must remain disabled."
  }
  assert {
    condition     = azurerm_linux_web_app.app.https_only && azurerm_linux_web_app.app.site_config[0].minimum_tls_version == "1.2"
    error_message = "App must require HTTPS and TLS 1.2."
  }
  assert {
    condition     = azurerm_key_vault.app.rbac_authorization_enabled && azurerm_key_vault.app.purge_protection_enabled
    error_message = "Vault RBAC and purge protection must be enabled."
  }
  assert {
    condition     = length(azurerm_sentinel_alert_rule_scheduled.auth_failures) == 0
    error_message = "Sentinel should be opt-in for cost control."
  }
}
run "sentinel_opt_in" {
  command = plan
  variables { enable_sentinel = true }
  assert {
    condition     = length(azurerm_sentinel_alert_rule_scheduled.auth_failures) == 1 && length(azurerm_sentinel_alert_rule_scheduled.vault_denied) == 1
    error_message = "Both detection rules must be present when Sentinel is enabled."
  }
}
