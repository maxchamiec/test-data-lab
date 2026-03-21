# Working with GitHub (this project)

This document describes how to use Git with **test-data-lab** when the remote is hosted on GitHub.

**Repository:** [https://github.com/maxchamiec/test-data-lab](https://github.com/maxchamiec/test-data-lab)

---

## Prerequisites

- [Git](https://git-scm.com/) installed on your machine.
- Access to the repository (public clone; push requires write access and authentication).

---

## First-time setup: clone

```bash
git clone https://github.com/maxchamiec/test-data-lab.git
cd test-data-lab
```

The default remote name is `origin`, and the default branch is `main`.

---

## Stay up to date before you work

Always pull the latest changes from GitHub before starting work or before pushing, especially if you use more than one computer:

```bash
cd test-data-lab
git pull origin main
```

If your local `main` only tracks `origin/main`, you can use:

```bash
git pull
```

---

## Check what changed locally

```bash
git status                 # staged / unstaged files
git diff                   # unstaged changes
git diff --staged          # staged changes (after git add)
```

---

## Commit your work

1. Stage files (do **not** commit `.venv/`, `output/`, or other ignored paths—they are listed in `.gitignore`):

   ```bash
   git add .
   # or add specific files:
   # git add README.md app.py
   ```

2. Create a commit with a clear message:

   ```bash
   git commit -m "Short description of the change"
   ```

3. Push to GitHub:

   ```bash
   git push origin main
   ```

   If `main` already tracks `origin/main`:

   ```bash
   git push
   ```

---

## If `git push` is rejected

The remote may have new commits you do not have locally.

1. Pull and integrate, then push again:

   ```bash
   git pull origin main --no-rebase
   git push origin main
   ```

   Resolve any merge conflicts if Git reports them, then `git add` the fixed files and `git commit` before pushing.

2. Alternatively, rebase your local commits on top of `main` (use only if you are comfortable with rebasing):

   ```bash
   git pull origin main --rebase
   git push origin main
   ```

---

## Optional: feature branches

For larger changes, use a branch and open a Pull Request on GitHub:

```bash
git checkout -b feature/my-change
# ... edit, commit ...
git push -u origin feature/my-change
```

Then create a PR from `feature/my-change` into `main` on the GitHub website.

---

## Authentication (HTTPS)

If you use **HTTPS** (as in the clone URL above), GitHub no longer accepts account passwords for Git operations. Use one of:

- A **Personal Access Token** (PAT) when Git asks for a password, or  
- **Git Credential Manager** / your OS keychain (e.g. macOS Keychain with `credential.helper osxkeychain`).

SSH remotes (`git@github.com:...`) are an alternative; change `origin` only if your team agrees on SSH.

---

## Useful links

- [GitHub Docs: Git basics](https://docs.github.com/en/get-started/using-git)
- [GitHub Docs: Managing remote repositories](https://docs.github.com/en/get-started/git-basics/managing-remote-repositories)
