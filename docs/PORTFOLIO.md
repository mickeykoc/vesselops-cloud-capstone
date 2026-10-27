# Turning this into your own strong portfolio project

A numerical rating is subjective. This package is designed for the engineering depth behind a strong entry-level portfolio: connected behavior, infrastructure, identity boundaries, failure cases, reproducibility and clear evidence. A cloud deployment and your own explanations still matter more than a feature list.

## Completion checkpoints

| Checkpoint | Your deliverable |
| --- | --- |
| Local operation | Your own screenshot, a created asset, ticket lifecycle and observed 409 stale update |
| Security understanding | Explain token handling, public app vs private DB and why missing inventory fails |
| Meaningful customization | A change you designed, its failing test before the fix and passing test after |
| Azure deployment | Resource diagram, source commit, successful deployment/readiness and sanitized inventory |
| Network and identity | Private DNS evidence, outside-network denial, scoped roles and passwordless DB access |
| Detection | Exported real console rows correlated to your scenario request IDs, verified KQL results |
| Operations | Actual cost record, teardown verification and a recreate run |
| Presentation | GitHub README, architecture diagram, incident writeup and short screen recording |

## Suggested personal change

Add per-user Entra authentication OR add paginated ticket queries with an explicit API contract. Pick one and implement it carefully. These are meaningful improvements, not renaming colors. Keep the generated starting point and your commits distinguishable. Do not claim the feature until completed.

## Three-minute walkthrough

- 0:00–0:30: what problem VesselOps models; explain local vs cloud status.
- 0:30–1:10: create/review a ticket; show history and stale-update protection.
- 1:10–1:50: trace managed identity and private endpoint on the diagram; show actual access tests if deployed.
- 1:50–2:30: show controlled failed-request IDs, exported logs and investigation conclusion.
- 2:30–3:00: demonstrate the policy failing on a bad fixture, explain one tradeoff and your change.

## Resume wording by actual completion

**After you personally run, understand and customize the local implementation:**

VesselOps — Cloud Operations & Security Lab | Python, Flask, SQLite, Terraform
- Customized and tested an operations console with authenticated APIs, asset-linked tickets, investigation history and optimistic concurrency control.
- Correlated controlled failed-authentication requests with incident evidence and evaluated Azure configuration guardrails against test exports.

**After your own successful Azure deployment and verification:**

VesselOps — Azure Cloud Operations Capstone | Azure, Terraform, GitHub Actions, Python
- Deployed an operations application to Azure App Service with managed-identity database access, a private Cosmos DB endpoint and scoped Key Vault secret permissions.
- Automated infrastructure validation and deployment using Terraform, GitHub OIDC and a policy gate for selected cloud security configurations.

**Only after live telemetry and detection verification:**
- Centralized application and service diagnostics in Log Analytics, validated KQL detections and documented an investigation using observed request IDs.

Do not list Entra user authentication, MFA, Active Directory, AWS deployment, SQL administration, live attacker monitoring or production experience from this package. Security+ belongs as in progress until earned. AI-assisted implementation can be discussed honestly: explain what you tested, changed and learned.
