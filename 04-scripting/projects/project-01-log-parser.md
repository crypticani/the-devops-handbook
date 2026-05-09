# Project: Log Parser Automation

## Problem Statement

Write a Bash or Python script that analyzes an application or web server log and produces a short operational report.

## Deliverables

- Script that accepts an input log file path
- Summary of total requests or events
- Top error codes or error messages
- Top source IPs or users where available
- Clear error handling for missing or unreadable files

## Validation

Run the script against sample data and capture output. Include at least one test with invalid input to prove the script fails clearly.

## Failure Scenario

Use a malformed log line or empty log file. Document how the script behaves and what you changed, if anything, to make the behavior safer.

## What to Commit

- Script source
- Sample input log
- Example output
- Failure notes

## Review Rubric

Use this rubric to self-assess your work or have a peer review it.

| Criteria | What to Look For | Score (1-5) |
|----------|-----------------|-------------|
| **Reproducibility** | Script runs with sample data included in the repo | |
| **Correctness** | Parsing output matches expected results for the given log format | |
| **Debugging quality** | Handles malformed lines, missing fields, and empty files gracefully | |
| **Security basics** | No shell injection risks; inputs are sanitized or quoted properly | |
| **Cleanup quality** | Temporary files are removed; script exits cleanly on errors | |
| **Explanation clarity** | Usage instructions, input format, and output format are documented | |

**Scoring**: 1 = Not attempted, 2 = Partial, 3 = Meets expectations, 4 = Exceeds expectations, 5 = Production quality
