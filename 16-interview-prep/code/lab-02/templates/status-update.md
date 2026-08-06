# Status Update Template

One update at declaration, then every 15–30 minutes until resolved, then a final one. Post them
even when there is no progress — silence is read as "nobody is working on it", and it is what
generates the stream of "any update?" messages that slow you down further.

Four lines. Written for whoever is answering customers, not for another engineer.

```text
[SEV2] Checkout — INVESTIGATING                                   14:52 UTC

Impact:   ~70% of checkout requests are failing with errors. Browsing and
          login are unaffected.
Status:   Errors started 14:41, shortly after the 14:38 release. Rolling
          back now.
Next:     Update by 15:10, or sooner if the rollback resolves it.
Lead:     @you (incident commander)
```

Rules that make the difference between a useful update and noise:

- **Impact in user terms.** "Connection pool exhausted" is a cause, not an impact. "Customers cannot complete checkout" is an impact.
- **Say what you do *not* know.** "Cause not yet confirmed" is a fine thing to write and far better than implying certainty you will have to retract.
- **Always give the next update time.** It is what stops people asking.
- **Never speculate about blame or root cause in a status update.** That goes in the postmortem, after you have evidence.

## Status progression

| Status | Means |
|--------|-------|
| `INVESTIGATING` | We know something is wrong, we do not yet know what |
| `IDENTIFIED` | We know the cause and are acting on it |
| `MONITORING` | Mitigation applied, watching to confirm recovery |
| `RESOLVED` | Impact ended. A postmortem is still owed |
