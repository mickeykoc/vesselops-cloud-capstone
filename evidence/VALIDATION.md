# Validation record

Prepared October 27, 2026. Results below are assistant-executed checks of the delivered source, not Michael's personal completion record.

| Check | Result | Scope |
| --- | --- | --- |
| Python test suite | 53 passed | Auth, ticket/asset/incident behavior, real localhost scenario, SQLite concurrency, Cosmos SDK adapter contracts, analyzers, policy, package allowlist, HCL security invariants |
| Application coverage | 96.17% of 261 statements | app/ only; does not measure cloud deployment completeness |
| Browser walkthrough | Passed | Connect, create ticket, investigate, display scenario evidence, lock clears records; no JavaScript page errors |
| Responsive browser check | Passed | 1440px desktop and 390px mobile; no horizontal page overflow at 390px |
| Ruff | Passed | Application, tools and tests |
| JavaScript syntax | Passed | node --check on app.js |
| Shell syntax | Passed | bash -n on both bootstrap scripts |
| Workflow syntax | Parsed successfully | YAML parsing only; no GitHub Actions execution |
| Runtime dependency audit | No known vulnerabilities reported | Pinned runtime requirements, audit snapshot on preparation date; not a future guarantee |
| Terraform formatting | Passed | Terraform 1.11.4 fmt -check |
| HCL parsing / static security invariants | Passed | Explicit DB isolation, managed identity, private endpoint wiring, vault protections and log destinations |
| Terraform provider installation | Completed with signed provider archives | AzureRM 4.62.0 and Random 3.7.2; lockfile included |
| Provider-backed terraform validate | Blocked by execution environment | Provider local Unix socket creation is denied; no successful provider schema validation claimed |
| terraform test with mocked providers | Supplied, not executed successfully here | Included for GitHub/local execution; depends on provider process startup |
| Live Azure apply / destroy | Not performed | No Azure account/session supplied |
| Live Cosmos private connectivity / identity | Not verified | SDK adapter contract tests use mocks, not Azure |
| KQL and Sentinel | Implemented, not live-verified | Needs ingested cloud tables, query execution and optional Sentinel enablement |
| GitHub publication / cloud workflow | Not performed | No repository/account connection supplied |
| Actual cloud cost / recreate exercise | Not measured | Requires user subscription deployment and teardown |

## Included evidence

- `python_tests.txt`: test summary and coverage.
- `coverage.json`: application-code coverage details.
- `dependency_audit.json`: dependency audit output.
- `browser_checks.json`: locally executed browser verification scope.
- `local_scenario.json`: controlled requests observed against a temporary local SQLite instance.
- `synthetic_azure_triage.json`, `synthetic_aws_triage.json`: results from explicitly synthetic export fixtures.
- `synthetic_secure_audit.json`, `synthetic_insecure_audit.json`: before/after fixture policy outputs.
- `../docs/console.png`, `../docs/console_mobile.png`: local console with synthetic records and cleared token field.

The screenshots and local scenario use temporary local storage. The database and token are not distributed. Configuration fixtures are authored samples, not collected cloud evidence. No screenshots contain a real account token or cloud portal session. The term "private database" describes the intended Terraform configuration until verified live.

## Reproduce

Follow README for the local environment, then run `pytest --cov=app`, `ruff check app tools tests` and `pip-audit -r requirements.txt --strict`. Optional browser verification: install requirements-browser.txt, run `python -m playwright install chromium`, then `python tools/check_browser.py`. To validate provider schemas/mocks on your own computer or GitHub runner: `terraform -chdir=infra init -backend=false`, `terraform -chdir=infra validate`, `terraform -chdir=infra test`. A separate fresh checkout is best for the backend-free tests; use the configured backend for deployment.
