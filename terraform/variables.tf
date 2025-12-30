variable "location" {
  type        = string
  description = "Azure region"
  default     = "West US 2"
}

variable "environment" {
  type        = string
  description = "Environment name (dev/staging/prod)"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "system_vm_size" {
  type = string
  description = "VM size for system node pool"
  default = "standard_dc2s_v3"
}


variable "user_assigned_identity_id" {
  type        = string
  description = "Resource ID of an existing user-assigned managed identity (optional)."
  default     = ""
}








