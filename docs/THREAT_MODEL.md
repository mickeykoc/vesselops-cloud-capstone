# Threat model and design decisions

## Assets and boundaries

Assets: operator token, operational records, incident evidence, Terraform state and cloud identity. Boundaries: browser to public HTTPS app; app identity to Key Vault; app to private Cosmos endpoint; GitHub OIDC identity to ARM/backend. All included example records are synthetic.

| Threat | Implemented control | Remaining limitation / required evidence |
| --- | --- | --- |
| Unauthorized operational reads or writes | Bearer auth on all data/readiness routes; constant-time comparison | One shared operator credential; no individual identity, MFA or user roles |
| Token leakage to browser storage or logs | Token held in tab memory; no localStorage; no request body/token logging; no redirects in scenario client | Token still exists in operator/browser/process memory and Terraform state; XSS could access it |
| Cross-site script injection | textContent rendering, no dynamic HTML insertion, restrictive CSP, Jinja autoescape | Browser dependency/UI changes need review; headers do not prove absence of every XSS issue |
| CSRF | No ambient authentication cookies; bearer header required | An attacker who obtains the bearer token can act as operator |
| Database credential theft | Cosmos account keys disabled; managed identity used | Compromised app can use its identity to access the dedicated account's data |
| Public DB access | public network disabled, private endpoint, private DNS, subnet NSG | Needs live DNS/reachability tests; public DNS resolution can still exist |
| Lost concurrent update | ETag / SQLite compare-and-swap and 409 | Ticket history is editable by a privileged DB actor; not tamper-proof audit storage |
| Evidence without provenance | Incident requires event IDs and source; structured app request IDs | Operator can enter misleading notes; not a forensic chain-of-custody system |
| Insecure infrastructure change | Named plan guardrails and provider-mocked tests | Limited rule set; pipeline identity can modify infrastructure/RBAC in the lab group |
| Excess spending | Manual deployment, budget notifications, ingestion quota, destroy instructions | Budgets/quotas are not a global immediate hard cap; App Service/private endpoint continue accruing |
| Dependency vulnerability | Pinned runtime versions and pip-audit gate | Snapshot result; future CVEs can fail later runs and require controlled upgrades |
| API abuse/availability | Input size, field lengths and history bounds | No distributed rate limiting, WAF or per-user quotas; list queries are unpaginated |

## Intentional decisions

1. **Cosmos instead of SQL:** a document can hold the current ticket plus bounded history and be updated atomically with an ETag. Managed-identity data access removes database-password bootstrap. Partitioning by kind suits a tiny lab but can create hot partitions at scale; this is not a claim of production data modeling.
2. **Public vault endpoint with RBAC:** permits operator/hosted Terraform runners to manage the secret. Runtime read is scoped to one secret. A private vault would require a trusted private runner/management path, which is not supplied here.
3. **Shared operator bearer auth:** keeps the app demonstrable without Entra app-registration provisioning. It does not implement Entra user login, Conditional Access, MFA or enterprise authorization. A next iteration could replace it with OIDC/Entra and per-user claims.
4. **Controlled scenario instead of honeypot:** known request IDs and expected outcomes allow repeatable evaluation without public attack exposure. This is a simulation of failed access, not exploitation.
5. **No NSG flow-log resource:** the source plan referenced old NSG flow logs. Microsoft no longer permits new NSG flow logs after June 30, 2025; see SOURCES. App, vault and data-plane diagnostics are implemented; packet-level/VNet flow logging is not implemented or claimed.
6. **No automatic deletion timer:** cleanup is explicit and verified. A timer could delete an in-progress lab or leave orphaned state; budget alerts alone cannot enforce a spend ceiling.

## Before handling real data

This is a synthetic-data portfolio lab. Multi-user auth, authorization, pagination, distributed throttling, log retention/PII review, backup restoration tests and operational monitoring require further engineering. Do not describe this as production-ready.
