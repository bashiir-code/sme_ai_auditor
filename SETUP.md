# Setup Guide

This document explains how to prepare the project locally for development and collaboration.

## 1. Initialize the repository

If this repository is not yet a Git repository, run:

```bash
git init
```

Then add the project files and create an initial commit:

```bash
git add .
git commit -m "chore: initial project setup"
```

## 2. Create the GitHub repository

1. On GitHub, create a new repository named `sme_ai_auditor`.
2. Add the remote to your local repo:

```bash
git remote add origin https://github.com/<your-org-or-username>/sme_ai_auditor.git
```

3. Push the main branch:

```bash
git branch -M main
git push -u origin main
```

## 3. Install system prerequisites

Required tools:

* Python 3.9+
* `curl`
* `git`
* `uv` (optional, but recommended)

Install `uv` with:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

## 4. Setup local Python environment

From the project root:

```bash
python -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

## 5. Configure environment variables

Copy the API template and fill in your keys:

```bash
cp .env.template_api .env
nano .env
```

Do not commit `.env` or secret keys.

## 6. Verify the setup

Run the project setup checker:

```bash
python verify_setup.py
```

## 7. Collaborating with a friend

* Add your friend as a collaborator on GitHub or invite them to the organization.
* Use feature branches for new work.
* Create pull requests for review.
* Use the GitHub Actions workflow in `.github/workflows/python-app.yml` to verify tests on each PR.

## 8. Recommended workflow

```bash
git checkout -b feature/<short-description>
# make changes
git add .
git commit -m "feat: add ..."
git push -u origin feature/<short-description>
```

Then open a pull request on GitHub.
