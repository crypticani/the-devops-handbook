# Project: Branching Workflow with Conflict Resolution

## Problem Statement

Build a small repository that demonstrates a realistic Git workflow: feature branches, pull request review, merge conflict, conflict resolution, and clean history inspection.

## Deliverables

- Repository with at least two feature branches
- One intentional merge conflict
- Conflict-resolution notes explaining the competing changes
- Final merged history that can be explained with `git log --oneline --graph --all`

## Validation

Capture command output showing:

- Branches before merge
- Conflict status from `git status`
- Resolved file diff
- Final commit graph

## Failure Scenario

Simulate committing to the wrong branch. Document how you detect it and recover using a new branch, cherry-pick, or reset strategy appropriate for local work.

## What to Commit

- Sample repo files
- `conflict-resolution.md`
- `recovery-notes.md`
