# Guardian AWS consumer-MVP backend

This is an intentionally small, single-region production MVP: CloudFront's
AWS-owned `*.cloudfront.net` HTTPS hostname is the only public entry point;
CloudFront reaches an internal ALB through a VPC origin; the ALB forwards only
requests carrying its private origin header to one EC2 API worker; and the API
uses encrypted, non-public PostgreSQL 16 with seven-day automated backups.

It does not modify Devo resources, require a purchased domain, use a public
database, expose SSH, upload raw child content, or enable CloudFront/ALB access
logs. The API's own request logger redacts one-time push action tokens.

## One-time bootstrap

Run this only from the AWS account-root session currently used to bootstrap the
account. AWS does not allow that root principal to assume a role, so it creates
or updates a CloudFormation-only `guardian-mvp-deployer` service role. The root
session only submits this named stack and CloudFormation performs stack resource
mutations through the constrained service role. No long-lived IAM user or
access key is created.

```bash
infra/aws/bootstrap-guardian-deployer.sh
```

## Deploy and validate

Push the exact branch first. The deployment script refuses to use an unpushed
or divergent branch, creates the Secrets Manager configuration only when it is
absent, provisions the stack, and then validates the public HTTPS endpoint,
readiness/migrations, WebSocket upgrade, ALB target health, and RDS privacy /
encryption / backup settings.

```bash
GUARDIAN_SOURCE_BRANCH=codex/aws-mvp-deploy infra/aws/deploy-production.sh
```

The final three output lines provide the AWS HTTPS base URL and the public
Ed25519 key/id that must be embedded in the Android release build. The private
seed, JWT secret, database password, origin header secret, and STS credentials
are never printed or committed.

## Cost and availability boundary

The stack uses one `t3.small` EC2 instance, one internal ALB, one single-AZ
`db.t4g.micro` RDS instance with 20 GiB gp3 storage, CloudFront data transfer,
CloudWatch logs (30 days), and Secrets Manager. This is a low-cost production
MVP, not an HA deployment: an AZ or EC2 failure interrupts service until
recovered. RDS has seven-day backups; a restore drill and multi-AZ RDS are the
next reliability upgrade.

Two CloudWatch alarms are created without actions because no approved alarm
recipient was discoverable. Add an SNS recipient and a Guardian-specific AWS
Budget before customer rollout.
