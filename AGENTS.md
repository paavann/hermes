# Hermes Workspace

Workspace instructions for AI agents. All commands run from the monorepo root (`.`). Never `cd` into child directories. List projects via `npx nx show projects`; each application and library maintains its own nested `AGENTS.md` for domain-specific details.

## 1. Commands

All commands run from the workspace root:

| Task                      | Command                                                                             |
| :------------------------ | :---------------------------------------------------------------------------------- |
| **Install**               | `npm ci && uv sync`                                                                 |
| **Dev (UI)**              | `npx nx dev hermes`                                                                 |
| **Dev (API)**             | `npx nx serve hermes-api`                                                           |
| **Dev (DB)**              | `docker compose up -d hermes-db`                                                    |
| **Create Migration**      | `npx nx run hermes-db:makemigrations -- -m "<msg>"`                                |
| **Apply Migration**       | `npx nx run hermes-db:migrate`                                                      |
| **Lint**                  | `npx nx lint <project>`                                                             |
| **Typecheck**             | `npx nx typecheck <project>`                                                        |
| **Test (Suite)**          | `npx nx test <project>`                                                             |
| **Test (Single TS File)** | `npx nx test <project> -- path/to/file.spec.ts`                                     |
| **Test (Single TS Case)** | `npx nx test <project> -- -t "<test_name>"`                                         |
| **Test (Single Py File)** | `npx nx test <project> -- tests/path/to/test_file.py`                                |
| **Test (Single Py Case)** | `npx nx test <project> -- -k <test_name>`                                           |
| **Format (TS)**           | `npx nx format:write --projects=<project>`                                          |
| **Format (Python)**       | `npx nx run <project>:format`                                                       |
| **Affected Check**        | `npx nx affected -t lint typecheck test --base=master`                              |

## 2. Invariants

- **Coordinates**: Derive coordinates exclusively via the geocoding pipeline in `libs/shared/hermes-ai` (cached, token-bucket rate-limited Nominatim client). Never accept LLM-generated coordinates; never call Nominatim directly (1 req/s policy).
- **Database Schemas**: Apply all schema alterations through Alembic migrations only. Raw SQL DDL and `create_all()` are strictly prohibited.
- **Contract Synchronization**: TypeScript response models in `libs/shared/util-types/src/lib/api-types.ts` are hand-mirrored from Pydantic schemas in `apps/hermes-api/src/hermes_api/schemas/events.py`. Update both together in the same task whenever contracts change.

## 3. Conventions

- **Thin Shells (`apps/` vs `libs/`)**: Applications in `apps/` contain routing, document shells, and top-level provider wiring only. All business logic, state stores, spatial math, and UI widgets reside in `libs/`.
- **Modular Feature Structure**: Decompose features into dedicated directories containing `index.ts` (public export), `types.ts` (contracts), `use-[feature].ts` (logic/state hook), and isolated subcomponent files. Avoid monolithic single-file implementations.
- **UI Primitives**: Install shadcn primitives via `npx shadcn@latest add <component> --cwd libs/shared/ui-components`. Place shared UI elements in `libs/shared/ui-components`, never inside `apps/hermes`.
- **Generators vs Manual Files**: Use Nx generators (`npx nx g ...`) exclusively when creating new monorepo libraries or applications. Internal feature files (`types.ts`, hooks, components) are created directly by hand.
- **Dependencies**: Adding, updating, or removing any dependency requires explicit user approval. Once approved, prefer the Nx target (e.g. `npx nx run <project>:add --name=<pkg>`), falling back to `npm install` (Node) or `uv add` (Python).

## 4. Gotchas & Landmines

- **SSR WebGL Isolation**: `apps/hermes` runs in SSR mode (`ssr: true`), but Mapbox GL requires browser globals (`window`, WebGL context). Never render Mapbox canvas directly during SSR; isolate it behind dynamic `React.lazy` boundaries with a fallback skeleton.
- **Database Availability**: The PostGIS container must be running (`docker compose up -d hermes-db`) before starting the API or applying migrations to prevent connection refused errors.
- **`nx affected` Base Branch**: Nx defaults to `--base=main`, which fails because this repo uses `master`. Always pass `--base=master`.

## 5. Boundaries & Environment

- **Production Protection**: Never run migrations, the worker, or any script against a production database or with production API keys. Read variable names from `.env.example` only. Before any destructive run, check the target environment with `grep '^DB_HOST=' .env` — never print or read the full file. Never place secret values in code or commits.
- **Migration History**: Never edit existing migration files in `libs/shared/hermes-db/migrations/versions/`; always create a new migration via the Alembic revision command.
- **Mandatory Approvals**: Agents must obtain explicit user approval before:
  1. Adding, updating, or removing dependencies in `package.json` or `pyproject.toml`.
  2. Executing database migrations (`npx nx run hermes-db:migrate`).
  3. Running `git commit` or `git push` (leave version control execution to the user).
  4. Modifying `.env` files or security credentials.
- **Protected Files**: Never manually edit lockfiles (`package-lock.json`, `uv.lock`).
- **Verification**: After completing a code task, run the Affected Check command from the Commands table. Skip it for conversational questions and intermediate edits; a targeted single check to debug a failure is fine.
- **Environment Reference**: Consult `.env.example` for required workspace variables (`ENV`, `API_PORT`, `FRONTEND_PORT`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `VITE_CLERK_PUBLISHABLE_KEY`, `CLERK_SECRET_KEY`) and `apps/hermes-api/.env.example` for AI keys (`LLM_API`, `LLM_MODEL`, `EMBED_API`, `EMBED_MODEL`). Never place secret values in code or commits.

## 6. Domain Triggers

- **When editing React UI or routes (`apps/hermes/`)**: Read `apps/hermes/AGENTS.md` and `.agents/rules/react-standards.md`.
- **When editing Mapbox GL layers, telemetry, or clustering (`libs/map/`)**: Read `libs/map/AGENTS.md`.
- **When editing REST endpoints or causality timelines (`apps/hermes-api/`)**: Read `apps/hermes-api/AGENTS.md`.
- **When editing RSS ingestion, Fargate worker, or geocoding (`apps/hermes-worker/` or `libs/shared/hermes-ai/`)**: Read `apps/hermes-worker/AGENTS.md` and `libs/shared/hermes-ai/AGENTS.md`.
- **When editing database schemas, models, or migrations (`libs/shared/hermes-db/`)**: Read `libs/shared/hermes-db/AGENTS.md`.
- **When writing Python code (`**/\*.py`)**: Read `.agents/rules/python-standards.md`.
- **When writing TypeScript code (`**/*.ts`, `**/*.tsx`)**: Read `.agents/rules/ts-standards.md`.

<!-- BEGIN AWS Agent Toolkit rules -->
# AWS Guidance for the new AWS experience

This user has signed up for the new AWS experience. This experience lets you sign into AWS using a social provider and requires the following additional context.

Where this guidance conflicts with the project's own instructions, the project's instructions take precedence.

## Context

### Terminology:

- Say "project" instead of "account" — a project contains an AWS account and settings for sharing with other collaborators
- Say "team member" instead of "IAM user" — users are invited by email, not created or federated in IAM
- Say "AWS Settings" when referring to management tasks at [settings.aws.com](https://settings.aws.com/) (project management, billing, team members, spend limits). Users view their actual AWS resources in the AWS Management Console.
- Say "selected Region" when referring to the user's Region — not "home Region"
- The user has a managed IAM experience. This includes a managed service control policies (SCP) and resource control policies (RCP) that govern the use of AWS. They will still need to use IAM to create policies to let services work with each other. If there are questions about the SCPs or RCPs, go to the documentation at https://docs.aws.amazon.com/accounts/latest/reference/scps-and-rcps-for-projects.html

### Constraints:

- All projects share a single AWS Region determined by the user's contact address. Resources cannot be created in other Regions
- When developing:
  - MUST create all Regional resources in the project's assigned Region
  - You CAN create AWS WAF and Cloudwatch Logs resources in us-east-1 when there are global resources (like a global WAF instance) that require a connection to dependencies in us-east-1. You should not use these for any other reason, because resources in the selected Region will provide lower cost (due to no cross-Region traffic), increased availability (due to no cross-Region traffic), and easier manageability (due to not needing to look in another Region). When you need to do an inventory of resources, you need to look in both the selected Region and us-east-1 for Cloudwatch Logs or WAF resources.
  - MUST NOT attempt to create Lambda, API Gateway, or other Regional resources in any other Region
  - MUST direct users to confirm their Region in AWS Settings > View all projects > Overview > Additional Info > Region. If the user cannot confirm their Region, check in ~/.aws/config
  - MUST NOT use Lambda@Edge — excluded from both Lambda and CloudFront
  - MUST NOT use CloudFormation StackSets — no multi-account or multi-Region deployments
  - MUST NOT attempt cross-Region actions — no cross-Region replication for DynamoDB/S3/RDS, no multi-Region KMS keys
  - MUST NOT use Route 53 cross-Region routing — geolocation, latency-based, and failover routing policies are not available
  - CloudFront is a global service and its actions ARE allowed in `us-east-1`. A user can create a CloudFront distribution pointing to their project-region Lambda function URL or API Gateway. However, Lambda and API Gateway themselves MUST NOT be created in `us-east-1` — they must be in the project Region.
  - Reduced availability in `eu-north-1` specifically: Amazon Rekognition, Amazon Textract, Amazon Personalize, AWS App Runner are not available in that Region.
- IAM permissions for human access are managed by AWS. Don't assign roles to team members unless absolutely necessary
- The user may have a spend limit if they are on the paid plan. The limit that pauses their project if it's exceeded. If resources suddenly become inaccessible, ask if they have a spend limit configured. Only project owners can modify a spend limit.
- When developing:
  - MUST ask about spend limit status if the user reports sudden "Access Denied" errors on operations that previously worked
  - MUST direct users to check spend status in AWS Settings > Billing
  - MUST check if a user has upgraded their account to the paid plan
  - MUST ask the user if they want to clean up the successfully created resources or keep them to reduce cost
- The user sets up billing, creates spend limits, and retrieves and pays invoices in AWS Settings. The user creates budgets and optimizes their costs in the AWS Billing and Cost Management console
- Not all AWS services are available. If a service isn't working, do the following:
  1. Run the command `aws freetier get-account-plan-state`
  2. If accountPlanType": "FREE", check the [Free Tier supported services list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-free-tier) next,
  3. If accountPlanType": "PAID", check the [Paid Tier supported services list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#supported-services-paid-plan).
  4. If neither list shows the service, check the [Not supported for this experience list](https://docs.aws.amazon.com/accounts/latest/reference/supported-services-sign-up-new.html#unsupported-services). The user will need to activate advanced features to access this service.
- Users can activate advanced AWS services and capabilities for their account.
- For any AWS task or question — building, configuring, migrating, debugging, or operating a service, writing SDK code, authoring CDK/CloudFormation, or answering how a service works — first call `aws___search_documentation` with topic `agent_skills` and load the matching skill with `aws___retrieve_skill`. Do this even when you believe you know the answer: skills carry current service behavior that your training may not. Prefer the skill's guidance over general knowledge. Skip it only for work that does not involve AWS.

### Help level

- help_level (required): LOW, MEDIUM, or HIGH. While a user is building, you MUST ask the user: "How much guidance would you like from me? Low (I only flag security risks), medium (I ask a couple of clarifying questions if something seems off), or high (I explain what I'm doing, suggest alternatives, and flag best practices)."

You CAN update this rule file to save a user's help_level.

Constraints for each level:

**LOW:**

- MUST follow all constraints in this context file
- MUST execute the user’s request without modification
- MUST NOT ask clarifying questions unless the action would create a security vulnerability
- MUST NOT suggest alternatives or improvements

**MEDIUM:**

- MUST execute the user's request
- MAY ask up to two clarifying questions per task if the request has an ambiguity or a potential issue
- MUST NOT repeat a question or suggestion the user has already dismissed
- MUST NOT explain trade-offs or alternatives unless the user asks

**HIGH:**

- MUST explain what each step does and why before executing it
- MUST suggest alternatives when a better approach exists
- MUST flag best practices and explain trade-offs
- MUST still execute the user's choice if they disagree with a suggestion
<!-- END AWS Agent Toolkit rules -->
