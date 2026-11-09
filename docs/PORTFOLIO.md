# Project roadmap and evidence checklist

The project is designed around the engineering depth expected of a strong entry level portfolio: connected behavior, infrastructure, identity boundaries, failure cases, reproducibility and clear evidence. A completed cloud deployment and clear explanations of the design carry more weight than the feature list.

## Completion checkpoints

| Checkpoint | Evidence |
| --- | --- |
| Local operation | Local console screenshot, a created asset, ticket lifecycle and observed 409 stale update |
| Security understanding | Explanation of token handling, public app vs private DB and why missing inventory fails |
| Meaningful customization | A designed change, its failing test before the fix and passing test after |
| Azure deployment | Resource diagram, source commit, successful deployment/readiness and sanitized inventory |
| Network and identity | Private DNS evidence, outside network denial, scoped roles and passwordless DB access |
| Detection | Exported real console rows correlated to the scenario request IDs, verified KQL results |
| Operations | Actual cost record, teardown verification and a recreate run |
| Presentation | GitHub README, architecture diagram, incident writeup and short screen recording |

## Suggested next change

Add per user Entra authentication or paginated ticket queries with an explicit API contract. Either option is a meaningful improvement rather than a cosmetic change. The generated starting point and later commits stay distinguishable in the project history. A feature is recorded as complete only after it has been implemented and tested.

## Three minute walkthrough

- 0:00 to 0:30: the problem VesselOps models; local vs cloud status.
- 0:30 to 1:10: create and review a ticket; ticket history and stale update protection.
- 1:10 to 1:50: trace managed identity and the private endpoint on the diagram; actual access tests if deployed.
- 1:50 to 2:30: controlled failed request IDs, exported logs and the investigation conclusion.
- 2:30 to 3:00: the policy failing on a bad fixture, one tradeoff, and the change made.

## Resume wording by completion stage

**After the local implementation has been run, understood and customized:**

VesselOps: Cloud Operations & Security Lab | Python, Flask, SQLite, Terraform
- Customized and tested an operations console with authenticated APIs, asset linked tickets, investigation history and optimistic concurrency control.
- Correlated controlled failed authentication requests with incident evidence and evaluated Azure configuration guardrails against test exports.

**After a successful Azure deployment and verification:**

VesselOps: Azure Cloud Operations Capstone | Azure, Terraform, GitHub Actions, Python
- Deployed an operations application to Azure App Service with managed identity database access, a private Cosmos DB endpoint and scoped Key Vault secret permissions.
- Automated infrastructure validation and deployment using Terraform, GitHub OIDC and a policy gate for selected cloud security configurations.

**Only after live telemetry and detection verification:**
- Centralized application and service diagnostics in Log Analytics, validated KQL detections and documented an investigation using observed request IDs.

## Scope notes

Entra user authentication, MFA, Active Directory, AWS deployment, SQL administration, live attacker monitoring and production experience are outside the scope of this project and are not claimed by it. Security+ is listed as in progress until earned. The starting implementation was built with AI assistance; `docs/MY_BUILD_LOG.md` is the record of hands on work performed with the project.
