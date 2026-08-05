# Rotation Drill — Production DB Password

Start time: ____

## 1. ROTATE (target: < 15 min)   ⭐ FIRST. Always first.
- [ ] Generate a new credential
- [ ] Deploy it to every consumer (list them — this is where drills find gaps)
- [ ] Verify the application works on the new credential
- [ ] Revoke the old one
- [ ] Confirm the old one now FAILS

## 2. ASSESS (in parallel)
- [ ] When was it pushed? How long was it exposed?
- [ ] Was the repo public? Forked? Indexed?
- [ ] Check the audit log for use from unknown sources
- [ ] Any data accessed that shouldn't have been?

## 3. CLEAN UP (hygiene, not remediation)
- [ ] git filter-repo to purge from history
- [ ] Force-push; every collaborator re-clones
- [ ] Ask the host to purge cached views and fork references

## 4. PREVENT
- [ ] Pre-commit secret scan
- [ ] Server-side push protection
- [ ] Move this secret to a manager so the next one is dynamic

## Findings
- Consumers I forgot about: ____
- Time to rotate:           ____
- What made it slow:        ____
