# We don't manage Firebase resources through Terraform anymore
# Instead, we just apply Firestore rules to the default database using Firebase CLI

output "firestore_rules_applied" {
  value       = null_resource.apply_firestore_rules.id
  description = "ID of the null_resource that applied Firestore rules to the default database"
}