# Module 03: Git — Cheat Sheet

> Command reference including the **"oh no" recovery section** you'll actually need. Concepts live in the [module README](./README.md).
> Cross-module daily commands: **[QUICK-REFERENCE.md](../QUICK-REFERENCE.md)**

**Jump to:** [Setup](#setup) · [Daily loop](#the-daily-loop) · [Branching](#branching) · [Remotes](#remotes--syncing) · [Inspecting](#inspecting-history) · [Undoing](#undoing-things--the-oh-no-section) · [Stash](#stashing) · [Rebase](#rebase--history-rewriting) · [Debugging](#using-git-to-debug) · [Secrets](#secrets--gitignore) · [Hooks](#hooks) · [gh CLI](#github-cli-gh) · [Conventions](#commit-message-conventions)

---

## Setup

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase true          # rebase instead of merge on pull
git config --global push.autoSetupRemote true # no more "--set-upstream" ⭐
git config --global core.editor "vim"
git config --global diff.colorMoved zebra     # highlight moved code differently
git config --global rerere.enabled true       # ⭐ remember conflict resolutions
git config --global fetch.prune true          # drop deleted remote branches on fetch

git config --list --show-origin               # every setting and which file set it
git config user.email                         # what's active in this repo

# Commit signing (many orgs require it)
git config --global commit.gpgsign true
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519.pub
```

**Useful aliases:**

```bash
git config --global alias.st  "status -sb"
git config --global alias.lg  "log --oneline --graph --decorate --all"
git config --global alias.last "log -1 HEAD --stat"
git config --global alias.unstage "restore --staged"
git config --global alias.amend "commit --amend --no-edit"
```

---

## The Daily Loop

```bash
git status                    # what's changed  (git status -sb for compact)
git diff                      # unstaged changes
git diff --staged             # staged changes  ⭐ review before committing
git diff main...HEAD          # everything your branch adds vs main
git diff --stat               # summary of files changed

git add file.txt
git add -A                    # everything, including deletions
git add .                     # everything under the current directory
git add -p                    # ⭐ interactively stage HUNKS — makes clean commits easy
git add -u                    # only already-tracked files

git commit -m "feat: add health endpoint"
git commit -am "fix: typo"    # add tracked files + commit (skips untracked)
git commit --amend            # rewrite the last commit (message and/or content)
git commit --amend --no-edit  # add staged changes to the last commit, keep message

git push
git push -u origin feature/x  # first push of a new branch
git pull                      # fetch + integrate
git fetch --all --prune       # update remote refs without touching your working tree
```

---

## Branching

```bash
git branch                              # local branches
git branch -a                           # + remote-tracking branches
git branch -vv                          # + upstream and ahead/behind counts  ⭐
git branch --merged main                # branches safe to delete
git branch --no-merged main             # branches with unmerged work

git switch -c feature/add-metrics       # create and switch (modern)
git checkout -b feature/add-metrics     # same thing (classic)
git switch main
git switch -                            # ⭐ back to the previous branch
git switch --detach abc1234             # inspect an old commit

git branch -m old-name new-name         # rename
git branch -d feature/done              # safe delete (refuses if unmerged)
git branch -D feature/abandoned         # force delete
git push origin --delete feature/done   # delete the remote branch

git merge feature/x
git merge --no-ff feature/x             # always create a merge commit
git merge --squash feature/x            # stage everything as one change
git merge --abort                       # bail out of a conflicted merge
```

### Conflict resolution

```bash
git status                              # lists "both modified" files
# Edit each file; remove <<<<<<< ======= >>>>>>> markers
git add resolved-file.txt
git commit                              # (merge) or: git rebase --continue

git checkout --ours  file               # ⚠️ during MERGE: keep the current branch's version
git checkout --theirs file              # ⚠️ during MERGE: keep the incoming version
                                        #    During REBASE these are SWAPPED
git diff --name-only --diff-filter=U    # list unresolved files
git merge --abort  /  git rebase --abort # start over
git mergetool                           # open a configured 3-way merge tool
```

> 💡 Enable `rerere` once (`git config --global rerere.enabled true`) and Git remembers how you resolved a conflict. On a long-running rebase where the same conflict reappears, it replays your resolution automatically.

---

## Remotes & Syncing

```bash
git remote -v
git remote add upstream https://github.com/original/repo.git
git remote set-url origin git@github.com:me/repo.git    # switch HTTPS → SSH
git remote rename origin old-origin
git remote show origin                  # ⭐ branch tracking + stale branch report

git fetch origin                        # download refs, change nothing locally
git fetch --all --prune                 # + delete refs to branches deleted upstream
git pull --rebase                       # replay your commits on top of upstream
git pull --ff-only                      # ⭐ refuse to create a surprise merge commit

git push
git push --force-with-lease             # ⭐ safe force: fails if someone else pushed
git push --force                        # ⚠️ never on a shared branch
git push origin --tags
git push origin HEAD:main               # push current branch to a differently-named remote branch

# Sync a fork
git remote add upstream https://github.com/original/repo.git
git fetch upstream
git switch main
git merge upstream/main        # or: git rebase upstream/main
git push origin main
```

---

## Inspecting History

```bash
git log --oneline -20
git log --oneline --graph --decorate --all      # ⭐ the whole topology
git log -p file.txt                             # commits + diffs for one file
git log --follow file.txt                       # ...across renames
git log --stat                                  # files changed per commit
git log --since="2 weeks ago" --until=yesterday
git log --author="alice"
git log --grep="fix.*timeout"                   # search commit MESSAGES
git log -S "getUserById"                        # ⭐ commits that ADDED/REMOVED this string
git log -G "regex"                              # commits whose diff matches a regex
git log main..feature                           # commits in feature but not main
git log --merges / --no-merges
git log --format='%h %an %ar %s'                # custom output

git show abc1234                                # a commit's message + diff
git show abc1234:path/to/file                   # a FILE as it was at that commit
git show HEAD~3                                 # three commits back

git blame file.txt                              # who last touched each line
git blame -L 40,60 file.txt                     # only lines 40-60
git blame -w -C file.txt                        # ignore whitespace and moved code  ⭐

git shortlog -sn                                # commit counts per author
git diff abc1234..def5678                       # between two commits
git diff main --stat                            # summary vs main
git tag -l --sort=-v:refname | head             # newest tags
git describe --tags                             # human-readable version of HEAD
```

**Ref shorthands:** `HEAD` current commit · `HEAD~3` three first-parents back · `HEAD^2` second parent of a merge · `main@{yesterday}` · `@{-1}` previous branch · `abc1234^{tree}`

---

## Undoing Things — The "Oh No" Section

**Work out where the change is first** (working directory → index → commit → pushed), then pick the row:

| Situation | Command |
|-----------|---------|
| Discard unstaged changes in one file | `git restore file.txt` |
| Discard **all** unstaged changes | `git restore .` ⚠️ unrecoverable |
| Unstage a file (keep the edits) | `git restore --staged file.txt` |
| Fix the last commit **message** | `git commit --amend` |
| Add a forgotten file to the last commit | `git add f && git commit --amend --no-edit` |
| Undo the last commit, keep changes **staged** | `git reset --soft HEAD~1` |
| Undo the last commit, keep changes **unstaged** | `git reset HEAD~1` (mixed, the default) |
| Undo the last commit and **throw the work away** | `git reset --hard HEAD~1` ⚠️ |
| Undo a commit that's **already pushed** | `git revert abc1234` ⭐ makes a new inverse commit — safe |
| Revert a merge commit | `git revert -m 1 <merge-sha>` |
| Restore a file from another commit | `git restore --source=abc1234 file.txt` |
| Restore a deleted file | `git restore --source=HEAD~1 path/to/file` |
| Recover a deleted branch | `git reflog` → find the SHA → `git switch -c name <sha>` |
| Recover from a bad `reset --hard` | `git reflog` → `git reset --hard HEAD@{2}` |
| Abandon a rebase midway | `git rebase --abort` |
| Undo a `git pull` | `git reset --hard ORIG_HEAD` |
| Clean untracked files | `git clean -n` (dry run) then `git clean -fd` ⚠️ |

### `git reflog` — your safety net

```bash
git reflog                       # every position HEAD has held, ~90 days
git reflog show feature/x        # for one branch
git reset --hard HEAD@{5}        # jump back to a previous state
git switch -c rescue abc1234     # rescue a commit from a deleted branch
```

> 💡 **Anything that was ever committed is recoverable via reflog**, including work on branches you deleted and commits you `reset --hard`'d away. Work that was *never committed* is not. That asymmetry is the entire argument for committing early and often — you can always tidy history later.

### The three resets

| | Commit history | Index (staged) | Working directory |
|---|---|---|---|
| `--soft` | moved back | **kept** | kept |
| `--mixed` (default) | moved back | reset | kept |
| `--hard` | moved back | reset | **wiped** ⚠️ |

---

## Stashing

```bash
git stash                                # shelve tracked modifications
git stash -u                             # ⭐ include untracked files
git stash push -m "wip: prometheus config" -- path/to/file
git stash list
git stash show -p stash@{0}              # view the diff
git stash pop                            # apply the newest and delete it
git stash apply stash@{1}                # apply but KEEP it in the list
git stash drop stash@{0}
git stash clear                          # ⚠️ delete all stashes
git stash branch fix/thing stash@{0}     # create a branch from a stash
```

---

## Rebase & History Rewriting

```bash
git rebase main                          # replay this branch on top of main
git rebase -i HEAD~5                     # ⭐ interactive: squash/reword/reorder/drop
git rebase --continue / --skip / --abort
git rebase --onto main old-base feature  # move a branch to a different base

git cherry-pick abc1234                  # apply one commit here
git cherry-pick abc1234^..def5678        # a range
git cherry-pick -n abc1234               # apply without committing
git cherry-pick --abort
```

**Interactive rebase verbs:**

| Verb | Effect |
|------|--------|
| `pick` | Keep the commit as-is |
| `reword` | Keep the change, edit the message |
| `edit` | Pause here so you can amend the content |
| `squash` | Merge into the previous commit, combine messages |
| `fixup` | Merge into the previous commit, **discard** this message |
| `drop` | Remove the commit entirely |
| `exec` | Run a shell command (e.g. tests) at this point |

```bash
# Autosquash workflow — clean up without an interactive editor
git commit --fixup=abc1234               # mark a commit as a fixup for abc1234
git rebase -i --autosquash HEAD~10       # Git orders and marks them for you  ⭐
```

> ⚠️ **The golden rule**: never rewrite history that other people have pulled. Rebase and amend are for your own unpushed work, or a branch only you are on — then push with `--force-with-lease`, never bare `--force`.

---

## Using Git to Debug

```bash
# Which commit introduced the bug? Binary search through history.
git bisect start
git bisect bad                      # current commit is broken
git bisect good v1.2.0              # this tag was fine
# Git checks out a midpoint; test it, then:
git bisect good      # or: git bisect bad
# ...repeat (log2 n steps) until Git names the culprit
git bisect reset

# Fully automated — Git runs your test script at each step
git bisect start HEAD v1.2.0
git bisect run ./scripts/reproduce-bug.sh    # ⭐ exit 0 = good, non-zero = bad
```

```bash
git log -S "problematicFunction" --oneline   # when was this code introduced/removed?
git log --all --oneline -- path/to/deleted-file   # history of a file that no longer exists
git diff v1.2.0..v1.3.0 -- config/           # what changed in config between releases
git blame -L 40,60 -w -C file.js             # who wrote these lines, ignoring reformatting
```

---

## Secrets & .gitignore

```bash
git check-ignore -v path/to/file        # ⭐ WHICH rule is ignoring this file?
git status --ignored
git rm --cached secrets.env             # stop tracking, keep the local file
git rm -r --cached .                    # re-apply .gitignore to everything
git add . && git commit -m "chore: apply gitignore"
```

**Essential `.gitignore` for DevOps repos:**

```gitignore
# Secrets and environment
.env
.env.*
!.env.example
*.pem
*.key
*_rsa
*.p12
credentials
.aws/
.kube/config

# Terraform
*.tfstate
*.tfstate.*
.terraform/
*.tfvars
!*.tfvars.example
crash.log

# Ansible
*.retry
vault-password*

# Build and dependencies
node_modules/
__pycache__/
*.pyc
venv/
dist/
build/
target/

# Editors and OS
.DS_Store
.idea/
.vscode/
*.swp
```

**Prevention beats cleanup:**

```bash
# Scan the working tree and history
gitleaks detect --source . --verbose
trufflehog git file://. --only-verified

# Pre-commit hook
pip install pre-commit
cat > .pre-commit-config.yaml <<'YAML'
repos:
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks: [{id: gitleaks}]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: detect-private-key
      - id: check-merge-conflict
      - id: end-of-file-fixer
      - id: trailing-whitespace
YAML
pre-commit install
```

**If a secret is already committed:**

```bash
# 1. ROTATE THE SECRET FIRST. Assume it is compromised the moment it is pushed.
# 2. Then purge it from history:
pip install git-filter-repo
git filter-repo --path secrets.env --invert-paths
# or replace the string everywhere:
printf 'AKIAIOSFODNN7EXAMPLE==>REDACTED\n' > replacements.txt
git filter-repo --replace-text replacements.txt
# 3. Force-push and tell every collaborator to re-clone.
```

> ⚠️ Rewriting history does **not** remove a secret from GitHub's cached views, forks, or anyone's local clone. Rotation is the fix; history rewriting is cleanup.

---

## Hooks

Local hooks live in `.git/hooks/` (not version-controlled). Share them via `pre-commit` or a tracked directory + `git config core.hooksPath`.

| Hook | Fires | Typical use |
|------|-------|-------------|
| `pre-commit` | Before the commit is created | Lint, format, secret scan, fast tests |
| `commit-msg` | After the message is written | Enforce Conventional Commits |
| `pre-push` | Before pushing | Run the test suite |
| `post-merge` | After a merge/pull | Reinstall dependencies |
| `pre-receive` | Server-side | Reject non-compliant pushes org-wide |

```bash
cat > .git/hooks/pre-commit <<'SH'
#!/usr/bin/env bash
set -e
if git diff --cached --name-only | grep -qE '\.(tf)$'; then
  terraform fmt -check -recursive || { echo "Run: terraform fmt -recursive"; exit 1; }
fi
git diff --cached -U0 | grep -nE '(AKIA[0-9A-Z]{16}|-----BEGIN .* PRIVATE KEY-----)' \
  && { echo "❌ Possible secret in staged changes"; exit 1; }
exit 0
SH
chmod +x .git/hooks/pre-commit

git commit --no-verify        # ⚠️ bypass hooks (use sparingly)
git config core.hooksPath .githooks     # share hooks via a tracked directory
```

---

## GitHub CLI (`gh`)

```bash
gh auth login
gh repo clone owner/repo
gh repo create my-project --public --clone

gh pr create --fill                          # title/body from your commits
gh pr create --title "feat: x" --body "..." --base main --draft
gh pr list / gh pr list --author @me
gh pr status                                 # ⭐ your PRs and what's blocking them
gh pr view 42 --web
gh pr checkout 42                            # check out someone's PR locally
gh pr diff 42
gh pr checks 42                              # CI status
gh pr review 42 --approve / --request-changes -b "..."
gh pr merge 42 --squash --delete-branch

gh issue create --title "Bug: ..." --label bug
gh issue list --assignee @me

gh run list                                  # recent Actions runs
gh run view 12345 --log-failed               # ⭐ only the failing step's logs
gh run watch                                 # live-follow the current run
gh run rerun 12345 --failed
gh workflow run deploy.yml -f environment=staging

gh secret set AWS_ACCESS_KEY_ID              # reads from stdin
gh secret list
gh release create v1.2.0 --generate-notes
gh api repos/:owner/:repo/branches/main/protection    # raw API access
```

---

## Commit Message Conventions

```
<type>(<optional scope>): <subject in imperative mood, ≤50 chars>

<body: WHY this change, not what — wrap at 72 chars>

<footer: BREAKING CHANGE: ... / Refs: #123>
```

| Type | Use for |
|------|---------|
| `feat` | A new feature |
| `fix` | A bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no behaviour change |
| `refactor` | Restructuring without behaviour change |
| `perf` | Performance improvement |
| `test` | Adding or fixing tests |
| `build` | Build system or dependencies |
| `ci` | Pipeline configuration |
| `chore` | Maintenance, tooling |
| `revert` | Reverting a previous commit |

```
feat(monitoring): add Prometheus alert for disk pressure

Nodes were filling up silently — the only signal was a failed
deploy hours later. Alerts at 85% (warning) and 95% (critical)
with a 10m `for:` so short bursts don't page anyone.

Refs: #482
```

**Good subjects** finish the sentence *"If applied, this commit will..."*: `add health endpoint`, `fix race in worker pool`. Not `added stuff`, `fixes`, `wip`.

---

<div align="center">

[← Module 03 README](./README.md) · [Resources](./resources.md) · [Labs](./labs/) · [Handbook Quick Reference](../QUICK-REFERENCE.md)

</div>
