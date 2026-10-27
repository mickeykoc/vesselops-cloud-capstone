data "azurerm_client_config" "current" {}
resource "random_string" "suffix" {
  length  = 8
  upper   = false
  special = false
}
resource "random_password" "operator" {
  length  = 48
  special = false
}
locals {
  suffix = random_string.suffix.result
  tags   = { project = "vesselops", environment = "lab", owner = var.owner, managed_by = "terraform" }
}
resource "azurerm_resource_group" "lab" {
  name     = "rg-vesselops-${local.suffix}"
  location = var.location
  tags     = local.tags
}
resource "azurerm_virtual_network" "lab" {
  name                = "vnet-vesselops"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.location
  address_space       = ["10.42.0.0/16"]
  tags                = local.tags
}
resource "azurerm_subnet" "app" {
  name                 = "snet-app-integration"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.lab.name
  address_prefixes     = ["10.42.1.0/24"]
  delegation {
    name = "app-service"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}
resource "azurerm_subnet" "private" {
  name                              = "snet-private-endpoints"
  resource_group_name               = azurerm_resource_group.lab.name
  virtual_network_name              = azurerm_virtual_network.lab.name
  address_prefixes                  = ["10.42.2.0/24"]
  private_endpoint_network_policies = "Enabled"
}
resource "azurerm_network_security_group" "private" {
  name                = "nsg-data"
  location            = var.location
  resource_group_name = azurerm_resource_group.lab.name
  tags                = local.tags
  security_rule {
    name                       = "AppToDatabaseTLS"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "10.42.1.0/24"
    destination_address_prefix = "10.42.2.0/24"
  }
  security_rule {
    name                       = "DenyOtherInbound"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}
resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id
  network_security_group_id = azurerm_network_security_group.private.id
}
resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = azurerm_resource_group.lab.name
  tags                = local.tags
}
resource "azurerm_private_dns_zone_virtual_network_link" "cosmos" {
  name                  = "cosmos-vnet"
  resource_group_name   = azurerm_resource_group.lab.name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos.name
  virtual_network_id    = azurerm_virtual_network.lab.id
  registration_enabled  = false
}
resource "azurerm_cosmosdb_account" "data" {
  name                          = "cosmos-vesselops-${local.suffix}"
  resource_group_name           = azurerm_resource_group.lab.name
  location                      = var.location
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  public_network_access_enabled = false
  local_authentication_disabled = true
  minimal_tls_version           = "Tls12"
  capabilities { name = "EnableServerless" }
  consistency_policy { consistency_level = "Session" }
  geo_location {
    location          = var.location
    failover_priority = 0
  }
  backup {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = 8
    storage_redundancy  = "Local"
  }
  tags = local.tags
}
resource "azurerm_cosmosdb_sql_database" "app" {
  name                = "vesselops"
  resource_group_name = azurerm_resource_group.lab.name
  account_name        = azurerm_cosmosdb_account.data.name
}
resource "azurerm_cosmosdb_sql_container" "records" {
  name                  = "records"
  resource_group_name   = azurerm_resource_group.lab.name
  account_name          = azurerm_cosmosdb_account.data.name
  database_name         = azurerm_cosmosdb_sql_database.app.name
  partition_key_paths   = ["/kind"]
  partition_key_version = 2
}
resource "azurerm_private_endpoint" "cosmos" {
  name                = "pe-cosmos"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.location
  subnet_id           = azurerm_subnet.private.id
  private_service_connection {
    name                           = "cosmos-sql"
    private_connection_resource_id = azurerm_cosmosdb_account.data.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "cosmos"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos.id]
  }
  tags = local.tags
}
resource "azurerm_key_vault" "app" {
  name                       = "kv-vessel-${local.suffix}"
  location                   = var.location
  resource_group_name        = azurerm_resource_group.lab.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  tags                       = local.tags
}
# Deployer manages only secrets in this dedicated lab vault. RBAC assignment requires
# separate control-plane authorization; see the bootstrap runbook.
resource "azurerm_role_assignment" "deployer_vault" {
  scope                = azurerm_key_vault.app.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}
resource "azurerm_key_vault_secret" "operator" {
  name         = "operator-token"
  value        = random_password.operator.result
  key_vault_id = azurerm_key_vault.app.id
  content_type = "VesselOps operator bearer token"
  depends_on   = [azurerm_role_assignment.deployer_vault]
}
resource "azurerm_service_plan" "app" {
  name                = "plan-vesselops"
  resource_group_name = azurerm_resource_group.lab.name
  location            = var.location
  os_type             = "Linux"
  sku_name            = "B1"
  tags                = local.tags
}
resource "azurerm_linux_web_app" "app" {
  name                                           = "vesselops-${local.suffix}"
  resource_group_name                            = azurerm_resource_group.lab.name
  location                                       = var.location
  service_plan_id                                = azurerm_service_plan.app.id
  https_only                                     = true
  virtual_network_subnet_id                      = azurerm_subnet.app.id
  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false
  identity { type = "SystemAssigned" }
  site_config {
    always_on           = true
    minimum_tls_version = "1.2"
    ftps_state          = "Disabled"
    http2_enabled       = true
    health_check_path   = "/health/live"
    app_command_line    = "gunicorn --bind 0.0.0.0:8000 --workers 2 --timeout 90 wsgi:application"
    application_stack { python_version = "3.12" }
  }
  app_settings = {
    APP_MODE                       = "azure"
    KEY_VAULT_URL                  = azurerm_key_vault.app.vault_uri
    COSMOS_ENDPOINT                = azurerm_cosmosdb_account.data.endpoint
    SCM_DO_BUILD_DURING_DEPLOYMENT = "true"
    ENABLE_ORYX_BUILD              = "true"
    PYTHONUNBUFFERED               = "1"
  }
  logs {
    application_logs { file_system_level = "Information" }
    http_logs {
      file_system {
        retention_in_days = 1
        retention_in_mb   = 25
      }
    }
  }
  tags = local.tags
}
resource "azurerm_role_assignment" "runtime_vault" {
  scope                = "${azurerm_key_vault.app.id}/secrets/${azurerm_key_vault_secret.operator.name}"
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_linux_web_app.app.identity[0].principal_id
}
resource "azurerm_cosmosdb_sql_role_assignment" "runtime_data" {
  resource_group_name = azurerm_resource_group.lab.name
  account_name        = azurerm_cosmosdb_account.data.name
  role_definition_id  = "${azurerm_cosmosdb_account.data.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_linux_web_app.app.identity[0].principal_id
  scope               = azurerm_cosmosdb_account.data.id
}
resource "azurerm_consumption_budget_resource_group" "lab" {
  name              = "vesselops-budget"
  resource_group_id = azurerm_resource_group.lab.id
  amount            = var.monthly_budget
  time_grain        = "Monthly"
  time_period { start_date = var.budget_start_date }
  notification {
    enabled        = true
    threshold      = 50
    operator       = "GreaterThanOrEqualTo"
    contact_emails = [var.budget_email]
  }
  notification {
    enabled        = true
    threshold      = 100
    operator       = "GreaterThanOrEqualTo"
    contact_emails = [var.budget_email]
  }
}
