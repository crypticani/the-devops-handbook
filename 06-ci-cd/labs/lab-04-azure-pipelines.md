# Lab 04: Azure Pipelines — Agents, Stages, and Approvals

## 🎯 Objective

Run a multi-stage Azure Pipelines build on an agent you own, translating the GitHub Actions concepts from Lab 01 into Azure DevOps vocabulary: stages and jobs, a self-hosted agent pool, step templates, artefacts between stages, and an environment that stops a deployment until someone approves it.

The lab is built around the constraint every new Azure DevOps organisation hits: **you get zero Microsoft-hosted parallel jobs until Microsoft approves a grant request**, which takes a few business days. Rather than wait, you run a self-hosted agent in Docker — free, immediate, and closer to what most enterprises actually operate.

---

## 📋 Prerequisites

- Read [§8 Azure Pipelines — The Enterprise Sibling](../README.md#8-azure-pipelines--the-enterprise-sibling)
- Completed [Lab 01: GitHub Actions](./lab-01-github-actions.md) — this lab is a translation of it
- Docker and Docker Compose, ~2 GB free
- A **free** Azure DevOps organisation ([dev.azure.com](https://dev.azure.com) — free for up to 5 users, no card). Exercise 1 and 2 need no account at all.

```bash
docker --version && docker compose version
```

---

## 📦 Deliverables and Evidence

- The agent image built, and the agent binary running before any credential exists
- Your agent listed as **Online** in the organisation's Default pool
- A pipeline run showing both stages, with the Deploy stage's artefact download
- The same `./ci.sh` output, produced locally and by the agent
- A run blocked on an approval, and the approval record that released it
- A pull request build that runs Build but not Deploy, and the condition that caused it
- `pipelines-notes.md`

---

## 📂 Lab Files

Reference copies are in [`../code/lab-04/`](../code/lab-04/).

```bash
cp -r /path/to/the-devops-handbook/06-ci-cd/code/lab-04/. .
chmod +x ci.sh agent/start.sh
```

```text
azure-pipelines.yml        the pipeline: two stages, a template, an environment
templates/
  steps-python.yml         a reusable step template
agent/
  Dockerfile               a self-hosted agent
  start.sh                 register → run one job → deregister
ci.sh                      ⭐ the build logic, called by both you and the pipeline
app/app.py                 the thing being built
docker-compose.yml         runs the agent
```

---

## 🔬 Exercise 1: The Pipeline, Read as a Translation

No account needed yet. Open `azure-pipelines.yml` next to Lab 01's workflow and read the mapping:

| GitHub Actions | Azure Pipelines | Note |
|----------------|-----------------|------|
| `on: push` | `trigger:` | Separate `pr:` block for pull requests — they are different triggers here |
| `jobs:` | `stages:` → `jobs:` → `steps:` | ⭐ One more level. Stages are the deployment boundary |
| `runs-on: ubuntu-latest` | `pool: { vmImage: ubuntu-latest }` | Or `pool: { name: Default }` for self-hosted |
| `uses: actions/setup-python@v5` | `task: UsePythonVersion@0` | Tasks are versioned by a number, not a tag or SHA |
| `run: ./ci.sh` | `script: ./ci.sh` | `script:` is bash on Linux, cmd on Windows; `bash:` forces bash |
| `${{ secrets.TOKEN }}` | `$(TOKEN)` | From a variable group or a secret variable |
| `actions/upload-artifact` | `publish:` / `download:` | Automatic in a `deployment:` job |
| composite action | `template:` | Also a **security** boundary — see §8 |
| `environment: production` | `environment: production` | Same idea, and where approvals live |

**Two differences worth internalising now**, because they cause most of the confusion:

1. **Stages run on different agents.** Anything Build produced is gone unless it was published as an artefact. In GitHub Actions the same is true across jobs; here the extra `stages` level means people hit it sooner.
2. **A `deployment:` job is not a `job:`.** Only a deployment job binds to an environment, and only an environment carries approvals, checks, and deployment history. Writing `job:` and wondering where the approval prompt went is the classic first mistake.

Run the build logic yourself — the same entry point the pipeline calls:

```bash
./ci.sh all
```

```text
── lint
   ✅ syntax ok
── test
app self-check: ok
── package (version 0.0.0-local)
   ✅ dist/app-0.0.0-local.tar.gz
```

⭐ **This is the habit the lab is really teaching.** The pipeline is a thin wrapper: provide an environment, call `./ci.sh`. Logic that lives only in YAML can only be tested by pushing a commit and waiting three minutes — which is how a one-line fix turns into eleven "fix pipeline" commits.

---

## 🔬 Exercise 2: Build the Agent

Still no account needed. The agent is a normal container: fetch Microsoft's agent tarball, unpack it, register on start.

```bash
docker compose build agent
docker run --rm --entrypoint sh azp-agent-test -c './config.sh --help | head -5' \
  2>/dev/null || docker compose run --rm --entrypoint sh agent -c './config.sh --help | head -5'
```

```text
./config.sh [options]

For unconfigure help, see: ./config.sh remove --help
```

The binary runs before any credential exists — worth confirming, because it separates "my Dockerfile is wrong" from "my token is wrong" later. Now watch it refuse to start without configuration:

```bash
docker compose run --rm --no-deps -e AZP_URL= -e AZP_TOKEN= agent
```

```text
/azp/start.sh: line 14: AZP_URL: set AZP_URL to https://dev.azure.com/<org>
```

> ⚠️ **The download host matters.** The older `vstsagentpackage.azureedge.net` CDN is being retired and already fails from some networks; the Dockerfile uses `download.agent.dev.azure.com`. If a build of this image ever fails with a curl error and nothing else, that is why.

---

## 🔬 Exercise 3: Connect It and Run the Pipeline

**This is where the free organisation is needed.** Five minutes:

1. Sign in at [dev.azure.com](https://dev.azure.com) and create an organisation and a project.
2. Push this lab directory to the project's repo (Repos → Files → clone URL).
3. Create a PAT: **User settings → Personal access tokens → New Token**, scope **Agent Pools (read, manage)**. Copy it — it is shown once.

```bash
export AZP_URL=https://dev.azure.com/<your-org>
export AZP_TOKEN=<the-pat>
docker compose up -d agent
docker compose logs -f agent
```

```text
Connecting to server ...
Successfully added the agent
Scanning for tool capabilities.
Listening for Jobs
```

Check **Project settings → Agent pools → Default → Agents**: yours is listed as **Online**.

Now create the pipeline: **Pipelines → New pipeline → Azure Repos Git → Existing Azure Pipelines YAML file → `/azure-pipelines.yml` → Run**.

You will see two stages, the second waiting on the first, and the `ci.sh` output identical to the run on your laptop.

> ⭐ **Why the agent exits after one job.** `run.sh --once` takes a single job and stops; `restart: unless-stopped` brings a fresh container back. Every job therefore starts on a clean machine — the ephemeral agent pattern. The alternative, a long-lived agent, is faster but lets job N inherit whatever job N-1 left behind, which is the source of "it only fails on agent 3" bugs.

---

## 🔬 Exercise 4: An Approval That Actually Blocks

Environments are where Azure Pipelines is genuinely stronger than a bare workflow file.

1. **Pipelines → Environments → New environment**, name it `staging`.
2. Open it → **⋮ → Approvals and checks → Approvals** → add yourself → Create.
3. Run the pipeline again.

The Deploy stage now sits at **Waiting**, and nothing in the deployment runs until you click Approve. The environment records who approved, when, and which build — the audit trail an auditor asks for and a chat message cannot provide.

```text
Build      ✅ succeeded
Deploy     ⏸ waiting for approval  ← 0 minutes of agent time consumed
```

⭐ **An approval is a *check on the environment*, not a step in the pipeline.** Every pipeline deploying to `staging` inherits it automatically, including one written next year by someone who never read this file. That is the difference between a control and a convention.

---

## 🧨 Break It: Four Azure Pipelines Failures

### Scenario 1: No Agent, No Error

**Break it.** Stop the agent and queue a build:

```bash
docker compose stop agent
# then: Pipelines → your pipeline → Run pipeline
```

**Symptom.** The run neither fails nor starts.

```text
Job build:  Queued  —  waiting for an available agent in pool Default
```

It waits like this for hours. No failure, no notification, no timeout that anyone would notice.

**Root cause.** Two different conditions produce this identical screen, and telling them apart is the skill:

| Cause | How to confirm | Fix |
|-------|----------------|-----|
| **No agent online** | Project settings → Agent pools → Default → Agents shows none, or all offline | Start the agent |
| **No parallelism grant** | Organization settings → Parallel jobs shows `0` hosted jobs | Use self-hosted, or submit Microsoft's grant request and wait |
| **Demands not met** | The job's log shows unmatched demands | Fix the demand, or install the capability on the agent |

⭐ **This is *the* Azure DevOps beginner experience**: a pipeline that looks correct and silently queues forever because a brand-new organisation has zero hosted parallelism. The pipeline is not broken — there is nowhere for it to run.

**Fix.**

```bash
docker compose start agent
```

### Scenario 2: The Artefact That Wasn't There

**Break it.** Remove the publish step — comment out the `publish:` block in the Build stage, commit, and run.

**Symptom.** Build is green. Deploy fails:

```text
##[error]No artifacts found for the deployment job
```

**Root cause.** Stages run on **different agents**, so `dist/` from Build simply does not exist in Deploy. It is not a permissions problem or a path problem; the file was never transported. A deployment job downloads artefacts automatically — but only artefacts that were published.

**Fix.** Restore the `publish:` step. And note the pairing: `publish:` in one stage, automatic download in a `deployment:` job, or an explicit `download:` in a plain job.

> ⚠️ **The same mistake with a worse ending**: a Deploy stage that *succeeds* because it deployed an empty directory. Check that your deploy step fails on a missing file rather than shipping nothing successfully.

### Scenario 3: The Variable That Didn't Cross

**Break it.** Set a variable in one job and read it in the next. Add to the Build job's steps:

```yaml
          - script: echo "##vso[task.setvariable variable=appVersion]1.2.3"
            displayName: Set a variable
          - script: echo "same job sees $(appVersion)"
            displayName: Read it here
```

…and in the Deploy stage's steps, `- script: echo "other stage sees '$(appVersion)'"`.

**Symptom.** The first prints `1.2.3`. The second prints an empty string, or the literal `$(appVersion)`, and does **not** fail.

**Root cause.** `setvariable` scopes to the job. Crossing a boundary requires saying so explicitly:

| Crossing | What you need |
|----------|---------------|
| Step → step, same job | `##vso[task.setvariable variable=x]` — works as-is |
| Job → job | `isOutput=true` on the set, and `dependsOn` plus an expression on the read |
| Stage → stage | The same, plus `stageDependencies` in the expression |

**Fix.**

```yaml
# in the producing job
- script: echo "##vso[task.setvariable variable=appVersion;isOutput=true]1.2.3"
  name: setVars                       # ⭐ the step needs a name to be referenced

# in a later job
variables:
  appVersion: $[ dependencies.build.outputs['setVars.appVersion'] ]
```

⭐ **An undefined variable expands to nothing and the build stays green.** That is the dangerous part — a deployment that tags an image `myapp:` and pushes it. Fail deliberately: `if [ -z "$(appVersion)" ]; then echo "appVersion is empty"; exit 1; fi`.

### Scenario 4: The Pull Request That Deployed

**Break it.** Delete the `condition:` on the Deploy stage, then open a pull request against `main`.

**Symptom.** The PR build runs Build **and Deploy**. Code that nobody has reviewed has reached staging.

**Root cause.** `pr:` triggers a full pipeline run, not a reduced one. Without a condition, every stage runs — including the one that deploys.

**Fix.** Restore it:

```yaml
    condition: and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))
```

**And do not rely on that alone.** Layer the controls the way the platform intends:

| Control | Where it lives | Can a pipeline edit bypass it? |
|---------|----------------|-------------------------------|
| `condition:` on a stage | The YAML file | ⚠️ Yes — the same PR can change it |
| Approval on the environment | Environment settings | ✅ No |
| Branch policy requiring review | Repos → Branch policies | ✅ No |
| `extends:` a template in a protected repo | Template repository | ✅ No — the pipeline can only do what the template allows |

⭐ **Anything enforced by the file being changed is not a control.** This is why Azure DevOps puts approvals on environments and checks on service connections rather than in the pipeline YAML — and why `extends:` templates exist. Secrets from a variable group are also withheld from fork PR builds for exactly this reason.

### Summary

| Failure | How you detect it | How you prevent it |
|---------|------------------|--------------------|
| Queued forever | Job stuck at "waiting for an available agent" | Alert on queue time; check pool and parallelism before blaming the YAML |
| Missing artefact | Deploy cannot find files Build made | `publish:` explicitly; make deploy steps fail on absent files |
| Variable didn't cross | An empty value and a green build | `isOutput=true` plus `dependencies`; assert the value is non-empty |
| PR deployed | A deployment triggered by a fork or PR build | Stage conditions **and** environment approvals **and** branch policies |

⭐ **The theme of this lab**: Azure Pipelines splits the pipeline (a file, editable by anyone who can open a PR) from the controls (environments, service connections, protected templates — editable only by administrators). GitHub Actions has been converging on the same split with environments and OIDC. Knowing which half a given safeguard lives in tells you whether it is a guardrail or a suggestion.

**Write this up** in `pipelines-notes.md`.

---

## 🧹 Cleanup

```bash
docker compose down
docker image rm lab-04-agent 2>/dev/null || true
```

The agent deregisters itself on exit (`config.sh remove` in the `trap`). Confirm the pool no longer lists it — a pool full of dead agents looks like capacity you do not have. Delete the organisation if you do not want to keep it; nothing here incurs a charge.

---

## ✅ Validation

- [ ] Map trigger, job, step, artefact, secret and environment between Actions and Pipelines
- [ ] Explain why a stage cannot see the previous stage's files
- [ ] Say what a `deployment:` job gives you that a `job:` does not
- [ ] Explain why a new organisation's pipeline queues forever, and two ways to fix it
- [ ] Pass a variable between jobs, and explain why the naive version fails silently
- [ ] Name which controls a pull request can bypass and which it cannot
- [ ] Explain the ephemeral agent pattern and the bug it prevents
- [ ] Justify keeping build logic in `ci.sh` rather than in the YAML

---

## 📝 What to Commit

- `azure-pipelines.yml`, `templates/steps-python.yml`, `ci.sh`, `agent/`
- A screenshot or log of your agent Online in the pool
- The two-stage run, and the Deploy stage's artefact download
- The approval record from the `staging` environment
- The PR run showing Build without Deploy
- `pipelines-notes.md` covering all four scenarios

> ⚠️ Never commit the PAT. It grants agent-pool management on your organisation — treat it as the credential it is, and revoke it when the lab is done.

---

[← Previous Lab: GitLab CI](./lab-03-gitlab-ci.md) | [Back to Module README](../README.md) | [Module 07: Observability →](../../07-observability/)
