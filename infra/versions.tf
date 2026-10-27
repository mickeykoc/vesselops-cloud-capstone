terraform {
  required_version = ">= 1.9, < 2.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "= 4.62.0" }
    random  = { source = "hashicorp/random", version = "= 3.7.2" }
  }
  backend "azurerm" {}
}
provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
  subscription_id                 = var.subscription_id
  resource_provider_registrations = "none"
}
provider "random" {}
