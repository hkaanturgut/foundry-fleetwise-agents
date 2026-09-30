output "resource_group" { value = azurerm_resource_group.rg.name }
output "foundry_account" { value = azapi_resource.foundry.name }
output "project_endpoint" { value = "https://${azapi_resource.foundry.name}.services.ai.azure.com/api/projects/${azapi_resource.project.name}" }
output "chat_deployment" { value = azapi_resource.chat.name }
output "acr_name" { value = azurerm_container_registry.acr.name }
output "api_url" { value = "https://${azurerm_container_app.api.ingress[0].fqdn}" }
output "embedding_deployment" { value = azapi_resource.embedding.name }
