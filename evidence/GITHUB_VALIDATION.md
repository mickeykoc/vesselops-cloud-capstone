# GitHub validation evidence

Validated October 27, 2026 by the repository's GitHub-hosted Ubuntu runner.

- Repository: https://github.com/mickeykoc/vesselops-cloud-capstone (private).
- Source commit tested: `cd4e93ae82097b78947b34cea2095aa5c0cc0ed4`.
- Successful run: https://github.com/mickeykoc/vesselops-cloud-capstone/actions/runs/40551966025
- Workflow: Validate and test.
- Run conclusion: success.

| Check | Observed result |
| --- | --- |
| Ruff | Passed |
| Python suite | 53 passed |
| Application coverage | 96.17% |
| Runtime dependency audit | No known vulnerabilities reported at run time |
| Terraform formatting | Passed |
| Terraform provider initialization | Passed with pinned signed providers |
| Terraform schema validation | Success: the configuration is valid |
| Mocked test: private_passwordless_data | Passed |
| Mocked test: sentinel_opt_in | Passed |
| Mocked test total | 2 passed, 0 failed |
| Insecure inventory policy | Rejected with expected failure exit code |
| Secure inventory policy | Passed |

## Actual issue found and fixed

The first GitHub run reached Terraform provider validation and failed because `health_check_path` requires a paired `health_check_eviction_time_in_min` setting in the pinned AzureRM provider. The source was corrected to set the interval to 2 minutes; the rerun passed validation and both infrastructure tests. This was a real CI configuration issue: the first run failed on the missing paired setting, the source was corrected, and the rerun passed.

## What this proves and what it does not

The source installs and passes these tests on a GitHub-hosted runner. Provider-backed validation checks the configuration schema; mocked tests do not create Azure resources. They do not establish private DNS behavior, real identity permissions, log ingestion, Sentinel detection results, cloud cost or successful Azure deployment. Those remain the next stage in docs/DEPLOY_AZURE.md. Personal completion evidence belongs in docs/MY_BUILD_LOG.md.
