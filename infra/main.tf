data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  name = "${var.prefix}-${random_string.suffix.result}"
  tags = { project = "fleetwise-agents", purpose = "demo" }
}

resource "azurerm_resource_group" "rg" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

# ---------- foundation: observability ----------
resource "azurerm_log_analytics_workspace" "law" {
  name                = "law-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "appi" {
  name                = "appi-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  workspace_id        = azurerm_log_analytics_workspace.law.id
  application_type    = "web"
  tags                = local.tags
}

# ---------- foundry: account, project, model, tracing connection ----------
resource "azapi_resource" "foundry" {
  type      = "Microsoft.CognitiveServices/accounts@2025-06-01"
  name      = "aif-${local.name}"
  parent_id = azurerm_resource_group.rg.id
  location  = var.location
  identity { type = "SystemAssigned" }
  body = {
    kind = "AIServices"
    sku  = { name = "S0" }
    properties = {
      allowProjectManagement = true
      customSubDomainName    = "aif-${local.name}"
      disableLocalAuth       = false
      publicNetworkAccess    = "Enabled"
    }
  }
  tags                      = local.tags
  schema_validation_enabled = false
  response_export_values    = ["properties.endpoint"]
}

resource "azapi_resource" "project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-06-01"
  name      = "proj-fleetwise"
  parent_id = azapi_resource.foundry.id
  location  = var.location
  identity { type = "SystemAssigned" }
  body = {
    properties = {
      displayName = "FleetWise agents"
      description = "Agents on top of the FleetWise legacy API"
    }
  }
  schema_validation_enabled = false
}

resource "azapi_resource" "chat" {
  type      = "Microsoft.CognitiveServices/accounts/deployments@2025-06-01"
  name      = var.chat_model.name
  parent_id = azapi_resource.foundry.id
  body = {
    sku = { name = var.chat_model.sku, capacity = var.chat_model.capacity }
    properties = {
      model = { format = "OpenAI", name = var.chat_model.name, version = var.chat_model.version }
    }
  }
  schema_validation_enabled = false
  depends_on                = [azapi_resource.project]
}

resource "azapi_resource" "appinsights_connection" {
  type      = "Microsoft.CognitiveServices/accounts/connections@2025-06-01"
  name      = "appi-tracing"
  parent_id = azapi_resource.foundry.id
  body = {
    properties = {
      category      = "AppInsights"
      target        = azurerm_application_insights.appi.id
      authType      = "ApiKey"
      isSharedToAll = true
      credentials   = { key = azurerm_application_insights.appi.connection_string }
      metadata      = { ApiType = "Azure", ResourceId = azurerm_application_insights.appi.id }
    }
  }
  schema_validation_enabled = false
}

# The presenter can create agents and run evaluations in the project.
resource "azurerm_role_assignment" "presenter_ai_user" {
  scope                = azapi_resource.foundry.id
  role_definition_name = "Foundry User"
  principal_id         = data.azurerm_client_config.current.object_id
}

# ---------- legacy: FleetWise API on Container Apps ----------
resource "azurerm_container_registry" "acr" {
  name                = replace("acr${local.name}", "-", "")
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

resource "azurerm_user_assigned_identity" "api" {
  name                = "id-api-${local.name}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

resource "azurerm_role_assignment" "api_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.api.principal_id
}

resource "azurerm_container_app_environment" "env" {
  name                       = "cae-${local.name}"
  location                   = azurerm_resource_group.rg.location
  resource_group_name        = azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
  tags                       = local.tags
}

locals {
  use_acr = var.api_image != "mcr.microsoft.com/k8se/quickstart:latest"
}

resource "azurerm_container_app" "api" {
  name                         = "ca-fleetwise-api"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = azurerm_resource_group.rg.name
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.api.id]
  }

  dynamic "registry" {
    for_each = local.use_acr ? [1] : []
    content {
      server   = azurerm_container_registry.acr.login_server
      identity = azurerm_user_assigned_identity.api.id
    }
  }

  ingress {
    external_enabled = true
    target_port      = local.use_acr ? 8080 : 80
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 1 # single replica: SQLite demo data lives in the container
    container {
      name   = "api"
      image  = var.api_image
      cpu    = 0.5
      memory = "1Gi"
    }
  }

  depends_on = [azurerm_role_assignment.api_acr_pull]
}
