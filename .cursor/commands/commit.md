Follow these steps in order.

## 1. Check changes since last push

- Run `./scripts/commit-check-changes.sh` to list changes since the last push (it runs `git fetch` and `git diff` against the upstream branch).
- Or manually: `git fetch origin`, then `git diff --name-status origin/<branch>`.
- Summarize what changed (backend, frontend, config, env, docs, scripts, tests).

## 2. Update documentation if needed before any commit or push

Based on the changed files, update docs only when the change warrants it

## 3. update CHANGELOG

- we want to keep track of all siginificant content changes in draft-martin-retry-over-ipv6.md
- we do not care much about formating changes unless they are significant

## 3. Commit and push

- Run `git status` to confirm what will be committed.
- Stage all intended changes: `git add …` (or `git add -A` if the full set is correct).
- Commit with a clear message that describes the change (e.g. "Add X", "Fix Y", "Update docs for Z"). Prefer conventional-style messages.
- **Push:** Run `git push origin <branch>`. You must run this with full permissions: use `required_permissions: ["all"]` when invoking the command, or the push will fail (Git cannot authenticate to GitHub from inside the sandbox and will report "could not read Username" / "Device not configured").

Never commit secrets, `.env`, or other sensitive files. If the user has uncommitted changes they don't want to include, ask before staging.