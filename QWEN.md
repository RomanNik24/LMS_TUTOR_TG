# Qwen Project Instructions

## 1. General rules

This repository is a Python project managed with Poetry.

Before making any changes:

1. Read this file completely.
2. Inspect the current repository state.
3. Run `git status`.
4. Run `git fetch origin`.
5. Make sure your work is based on the latest `origin/main`.
6. Never modify `main` directly.

Never assume that an old Qwen branch is up to date. Always compare it with the current `origin/main`.

---

## 2. Git workflow

Every task must be performed in a separate feature/fix branch created from the latest `origin/main`.

Recommended branch names:

* `feature/...`
* `fix/...`
* `refactor/...`
* `chore/...`

Never work directly on `main`.

Never use:

```bash
git push --force
git push --force-with-lease
git reset --hard
```

unless the user explicitly requests it and the consequences have been explained first.

Do not rewrite published history.

Do not merge Pull Requests automatically.

The normal workflow is:

```text
origin/main
   ↓
new feature/fix branch
   ↓
implementation
   ↓
tests
   ↓
commit
   ↓
Pull Request
   ↓
human review
   ↓
merge into main
```

---

## 3. Keep main authoritative

`main` is the authoritative branch.

Before starting a new task:

```bash
git fetch origin
git status
```

Create the task branch from the latest:

```bash
git checkout -b <branch-name> origin/main
```

Do not continue using an old task branch for a new unrelated task
