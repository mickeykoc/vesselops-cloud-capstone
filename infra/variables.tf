variable "subscription_id" {
  type        = string
  description = "Target Azure subscription UUID."
  validation {
    condition     = can(regex("^[0-9a-fA-F-]{36}$", var.subscription_id))
    error_message = "Provide the subscription UUID."
  }
}
variable "location" {
  type    = string
  default = "eastus2"
}
variable "owner" {
  type        = string
  description = "Owner alias for resource tags; no personal contact information."
  default     = "michael-nwokocha"
}
variable "enable_sentinel" {
  type        = bool
  default     = false
  description = "Enable only for the detection exercise after reviewing ingestion costs."
}
variable "budget_email" {
  type        = string
  description = "Address for resource-group budget notifications."
  validation {
    condition     = can(regex("^[^@ ]+@[^@ ]+\\.[^@ ]+$", var.budget_email))
    error_message = "Provide a valid budget notification email."
  }
}
variable "monthly_budget" {
  type        = number
  default     = 25
  description = "Budget notifications are alerts, not a spending cap."
  validation {
    condition     = var.monthly_budget > 0
    error_message = "Budget must be positive."
  }
}
variable "budget_start_date" {
  type        = string
  description = "First day of current month at midnight UTC, for example 2026-10-01T00:00:00Z."
  validation {
    condition     = can(regex("^20[0-9]{2}-[0-9]{2}-01T00:00:00Z$", var.budget_start_date))
    error_message = "Use the first day of a month at midnight UTC."
  }
}
