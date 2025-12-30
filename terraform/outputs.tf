output "aks_kube_config" {
  value     = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive = true
}


output "storage_account_name" {
  value = azurerm_storage_account.datalake.name
}


