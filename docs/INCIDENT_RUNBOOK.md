# Controlled incident investigation

## Scenario: five rejected operator requests

Run `tools/scenario.py` against your own local or Azure instance. The tool first verifies authenticated readiness, then sends five intentionally invalid tokens. The expected result is five HTTP 401 responses with unique request IDs, followed by a valid authenticated session and a created incident/ticket.

1. **Validate the signal.** Preserve request IDs and timestamps from the scenario result; export the relevant AppServiceConsoleLogs. Compare actual structured `auth.failed` rows with the response IDs. Do not infer the five requests reached the same five-minute KQL bucket without checking time boundaries.
2. **Establish scope.** Check the app resource, window and deployment history. A shared bearer token identifies no individual. The app does not trust caller-supplied forwarding headers as a user identity; the rule aggregates by resource, not attacker IP.
3. **Investigate.** Confirm whether an authorized operator or test generated the requests. Check nearby successful ticket operations, app errors and Key Vault denied requests. Omitted success-login logs mean you cannot reconstruct every authentication success from this schema.
4. **Decide.** Controlled scenario: close as expected authorized testing. Unknown source: preserve evidence, restrict app exposure if needed, rotate the operator token, restart all workers and check resource access. Do not automatically rotate or delete cloud resources from an unverified alert.
5. **Document.** Add an incident summary and related ticket notes. Distinguish observed facts, hypotheses and actions. Record what remains unknown.
6. **Verify.** Confirm invalid token is rejected, valid token works, no unexpected configuration change remains, and the ticket can be resolved with evidence.

## Incident report template

- Identifier / date / investigator:
- Environment and source (synthetic, local observed, cloud observed):
- Summary:
- Timeline with actual request/event IDs:
- Detection rule and threshold:
- Confirmed scope and limitations:
- Expected activity or suspicious activity, with reasoning:
- Containment/recovery actions actually performed:
- Verification result:
- False-positive considerations:
- Improvements and follow-up owner:

The included scenario-generated notes are demonstration content. Write your own analysis after running it. A rejected request alone is not evidence of a compromise or an attacker being blocked from an otherwise vulnerable system.
