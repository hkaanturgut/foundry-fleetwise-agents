variable "subscription_id" { type = string }
variable "location" {
  type    = string
  default = "eastus2"
}
variable "prefix" {
  type    = string
  default = "fleetwise"
}
variable "chat_model" {
  type = object({ name = string, version = string, sku = string, capacity = number })
  default = { name = "gpt-4o", version = "2024-11-20", sku = "GlobalStandard", capacity = 100 }
}
variable "api_image" {
  description = "FleetWise API image. Placeholder until the first az acr build."
  type        = string
  default     = "mcr.microsoft.com/k8se/quickstart:latest"
}
