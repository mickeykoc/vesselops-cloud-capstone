# Primary design references

Consulted while preparing this implementation on October 27, 2026. These references inform the design; they do not certify successful deployment.

- Azure Cosmos DB Private Link: https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-configure-private-endpoints
- Cosmos DB Entra/RBAC access: https://learn.microsoft.com/en-us/azure/cosmos-db/how-to-connect-role-based-access-control
- App Service VNet integration and outbound vs inbound scope: https://learn.microsoft.com/en-us/azure/app-service/overview-vnet-integration
- App Service GitHub Actions / OIDC: https://learn.microsoft.com/en-us/azure/app-service/deploy-github-actions
- Azure network monitoring and NSG flow-log replacement: https://learn.microsoft.com/en-us/azure/networking/design-guide/monitor
- Terraform AzureRM 4.62.0 provider source schemas: https://github.com/hashicorp/terraform-provider-azurerm/tree/v4.62.0/website/docs/r
- CloudTrail record schema: https://docs.aws.amazon.com/awscloudtrail/latest/userguide/cloudtrail-event-reference-record-contents.html

AzureRM is pinned to 4.62.0 and Random to 3.7.2. Runtime dependencies are pinned in requirements.txt. Upgrade them deliberately and rerun verification. GitHub Actions references use major tags for readability; a production repository should pin reviewed immutable commit SHAs and use dependency updates.

Concept source: user-provided Jhante Charles Lab Path Combined Capstone Plan. Implementation and layout were created here; the package does not contain or claim authorship of Jhante's original lab code.
