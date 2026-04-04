# Contributing to SME AI Auditor

Thank you for collaborating on SME AI Auditor! This document explains how to contribute code, run tests, and work together via GitHub.

## Getting Started

1. Fork or clone the repository:

```bash
git clone https://github.com/<your-org-or-username>/sme_ai_auditor.git
cd sme_ai_auditor
```

2. Create a feature branch:

```bash
git checkout -b feature/<short-description>
```

3. Install dependencies and set up your environment as described in `SETUP.md`.

## Branch and Commit Guidelines

* Use descriptive branch names like `feature/add-report-generator` or `fix/bug-123`.
* Keep commits small and focused.
* Use clear commit messages, for example:
  * `feat: add new compliance report template`
  * `fix: correct docling parser error handling`
  * `chore: update development docs`

## Environment and Secrets

* Copy `.env.template_api` to `.env`.
* Populate your API keys locally.
* Never commit `.env` or any secret credentials.

## Running Tests

Run the test suite before opening a pull request:

```bash
source .venv/bin/activate
pytest
```

If only a subset of tests is needed, run:

```bash
pytest tests/unit
pytest tests/integration
pytest tests/compliance
```

## Pull Requests

* Push your branch to GitHub.
* Open a pull request against `main`.
* Add a short description of your changes.
* Include testing notes and any manual verification steps.

## Code Review

* Reviewers should check functionality, style, and documentation.
* Update the PR if requested.
* Merge only after approvals and passing CI.

## Issues and Collaboration

* Use GitHub Issues to track bugs and enhancements.
* Label issues clearly: `bug`, `enhancement`, `documentation`, etc.
* Assign issues or request review from your collaborator.

## GitHub Actions

This repository includes a GitHub Actions workflow at `.github/workflows/python-app.yml` that runs tests on push and pull requests.

## Helpful Tips

* Run `git pull --rebase origin main` before starting work.
* Keep dependencies up to date carefully.
* Communicate with your collaborator by linking PRs and issues.
