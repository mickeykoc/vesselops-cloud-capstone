# Getting started

VesselOps is a combined capstone project: an operations console that connects an IT issue to an asset, preserves investigation history, and records security evidence, together with Azure infrastructure code, delivery workflows, logging, and configuration checks. The application runs locally with SQLite persistence or against an Azure Cosmos DB data path.

## Walkthrough

1. Open `README.md` for screenshots and local startup instructions.
2. Run the application locally.
3. Register an asset and work a ticket through investigation and resolution.
4. Run the controlled scenario and review its request IDs and incident conclusion.
5. Deploy to Azure following `docs/DEPLOY_AZURE.md`.
6. Collect cloud evidence per `docs/PORTFOLIO.md` and record working sessions in `docs/MY_BUILD_LOG.md`.

## Validation status

Built and tested locally: 53 passing tests, 96.17% application coverage, a browser tested desktop and mobile UI, and a completed synthetic incident workflow. Terraform validation and both provider mocked infrastructure tests passed on GitHub Actions.

## The Azure stage

The Azure stage requires an Azure subscription. It covers deployment, private connectivity verification, live logs and Sentinel, and cost and teardown evidence. Azure credit options for students are described in `docs/STUDENT_PACK.md`. Read `evidence/VALIDATION.md` for the exact verification status of each check.

Project evidence is collected in the evidence folder as each stage is completed.
