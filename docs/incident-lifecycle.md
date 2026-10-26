
# WebOps Intelligence — Incident Lifecycle

## Definitions

Check:
A single monitoring attempt against an authorized website.

Failure:
A check that does not satisfy the configured availability policy.

Incident:
A tracked operational problem created after the failure threshold is reached.

Recovery:
A return to successful monitoring checks after an incident.

Verified Resolution:
A previously open incident that has satisfied the configured recovery threshold.

## Initial Monitoring Policy

- Failure threshold: 3 consecutive failed checks.
- Recovery threshold: 2 consecutive successful checks.
- Default failure conditions: HTTP 5xx, connection errors, and timeouts.
- HTTP 4xx responses are recorded but are not outages by default.
- One active availability incident per website.
- Monitoring results and incident history are retained.

## States

### Healthy
The latest monitoring checks satisfy the availability policy.

### Suspected Failure
One or two consecutive checks have failed. No incident has been opened yet.

### Open
The failure threshold has been reached and an incident has been created.

### Recovering
An open incident has received its first successful recovery check.

### Verified Resolved
The recovery threshold has been met and the incident is closed.

## Transitions

Healthy → Suspected Failure:
A monitoring check fails.

Suspected Failure → Healthy:
A successful check resets the consecutive failure counter.

Suspected Failure → Open:
The failure threshold is reached.

Open → Recovering:
The first successful recovery check is recorded.

Recovering → Open:
A new failed check occurs before recovery is verified.

Recovering → Verified Resolved:
The recovery threshold is reached.

Verified Resolved → Suspected Failure:
A new failure sequence begins. A new incident may open if the threshold is reached.

## Acknowledgement

Acknowledgement is tracked separately from technical status.

Acknowledging an incident does not close it or prove recovery.

## Investigation

Each incident may contain:
- Monitoring evidence
- Diagnostic observations
- AI-generated hypotheses
- Recommended actions
- Manual or approved remediation records
- Verification results
- Timeline events

## Resolution Rules

- AI cannot directly mark incidents as resolved.
- A remediation action does not automatically prove recovery.
- Recovery must be supported by fresh monitoring evidence.
- Incidents remain available for historical review.