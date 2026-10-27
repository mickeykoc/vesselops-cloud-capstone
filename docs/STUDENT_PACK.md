# Using your GitHub Student Developer Pack

Your student benefits can help fund the real deployment, but they do not automatically connect either account to this project.

As checked October 27, 2026, the GitHub pack lists an Azure student offer with $100 credit. Microsoft's Azure for Students page describes $100 to use within 12 months and no credit card required, subject to student eligibility and activation. Check your own redeemed subscription and remaining balance; possessing the GitHub pack is not proof that Azure credit has been activated or remains available.

1. Open https://education.github.com/pack and select the Microsoft Azure offer shown in your account.
2. Redeem through the offered flow, or review https://azure.microsoft.com/en-us/free/students/ . Use your own eligible account; do not send passwords or tokens in chat.
3. In Azure, confirm the exact subscription, credit balance/expiry and allowed regions before running the deployment.
4. Use that subscription UUID in the capstone setup. Review the region's resource availability if a student-subscription policy rejects a SKU.
5. Keep Sentinel off until the logging exercise, collect evidence during short lab sessions, then destroy tracked resources.

The App Service **B1** plan used for VNet integration is not the free shared App Service tier. Cosmos DB **serverless** here is not the provisioned-throughput Cosmos free-tier allocation. Private endpoints and log ingestion can also consume credit. Do not assume a free-service listing covers this exact architecture. The $25 lab budget sends alerts, not a hard spending stop. The separately bootstrapped state storage account also has costs outside that resource-group budget.

GitHub account access is useful to publish the repository, run CI and configure the OIDC environment. The source package is ready for a repository, but no repository, credit redemption or cloud deployment has been performed in this delivery.

Sources:
- GitHub: https://education.github.com/pack?sort=popularity&tag=Cloud
- Microsoft: https://azure.microsoft.com/en-us/free/students/
