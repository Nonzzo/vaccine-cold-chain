provider "azurerm" {
  features {}
  subscription_id = "9d5850ea-385e-4eb6-be47-cbac9033c245" 
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-vaccine-platform"
  location = var.location
}

locals {
  common_tags = {
    Environment = var.environment
    Project     = "VaccineIntegrity"
  }
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-vaccine-cluster"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "vaccineaks"

  default_node_pool {
    name       = "default"
    node_count = 1
    vm_size    = var.system_vm_size
  }

 
  identity {
    type         = "UserAssigned"
    identity_ids = var.user_assigned_identity_id != "" ? [var.user_assigned_identity_id] : []
  }

  tags = local.common_tags
}





# Storage Account (Data Lake)
resource "azurerm_storage_account" "datalake" {
  name                     = "vaccinelake${var.environment}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  is_hns_enabled           = true  # Enable hierarchical namespace for Data Lake Gen2

  tags = local.common_tags
}

resource "azurerm_storage_data_lake_gen2_filesystem" "datalake_fs" {
  name               = "sensor-data"
  storage_account_id = azurerm_storage_account.datalake.id
}
