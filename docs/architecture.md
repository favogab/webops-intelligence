
# WebOps Intelligence — System Architecture

## Architecture Style

WebOps Intelligence uses a modular monolith built with Python and FastAPI.

The initial system runs as a self-hosted application with a relational database and scheduled monitoring jobs.

## Main Components

### API Layer — app/api/

Handles HTTP requests, validation, and responses.

### Core Layer — app/core/

Manages configuration, logging, security policies, and shared infrastructure.

### Monitoring Engine — app/monitoring/

Performs HTTP/HTTPS checks and generates structured monitoring results.

### Incident Engine — app/incidents/

Evaluates failure thresholds, manages incident states, and verifies recovery.

### Intelligence Engine — app/intelligence/

Provides deterministic diagnostic rules and optional AI-assisted incident analysis.

AI responses must be grounded in collected evidence, validated, and treated as advisory.

### Integrations — app/integrations/

Provides interfaces for optional CMS, hosting, and infrastructure connections.

### Dashboard — app/templates/

Displays monitored websites, incidents, investigations, and operational history.

### Database

PostgreSQL stores websites, monitoring checks, incidents, actions, and event history.

### Scheduler

A scheduled worker triggers monitoring checks at configured intervals.

## Data Flow

1. An operator registers an authorized website.
2. The scheduler requests a monitoring check.
3. The monitoring engine validates the target and performs the check.
4. The result is persisted.
5. The incident engine evaluates the result against the monitoring policy.
6. When an incident opens, diagnostic evidence is collected.
7. Rule-based and optional AI analysis generate recommendations.
8. An operator records or approves a supported corrective action.
9. Fresh monitoring checks verify recovery.
10. The incident timeline records the outcome.

## Security Boundaries

- Only HTTP/HTTPS targets are supported initially.
- Targets require authorization and validation.
- Requests to loopback, private, link-local, and other prohibited network destinations are blocked.
- DNS resolution and redirects require additional safety checks.
- Credentials are never sent to AI providers as incident context.
- AI cannot execute unrestricted commands.
- Remediation actions require explicit authorization.
- Management interfaces must not be publicly exposed without authentication.

## AI Operating Modes

Disabled:
Monitoring and deterministic diagnostics only.

Local:
AI analysis through a locally hosted model.

Remote:
Optional integration with a configured external AI provider.

The core monitoring and incident workflow must remain functional when AI is unavailable.

## Deployment Goal

A developer should be able to clone the repository, configure environment variables, run database migrations, start the application with Docker Compose, and reproduce the documented monitoring and incident workflow.

## Future Extensions

- Additional CMS connectors
- Hosting-provider integrations
- Controlled remediation workflows
- Multiple operator roles
- Advanced trend analysis
- Conversational incident investigation