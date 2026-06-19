# Setup — Developer / Technical Reference

> **Not a developer?** See [docs/quickstart.md](quickstart.md) for a step-by-step
> guide written for non-technical users.

This document covers installation, environment configuration, and content setup for
anyone contributing to or maintaining jobjob.

---

## Prerequisites

- Python ≥ 3.12
- [pdm](https://pdm-project.org/) (recommended) or plain `pip`

## Install

```sh
pdm install          # recommended — installs all dependency groups
# — or —
pip install -e .     # installs the package in editable mode
```

## Environment configuration

Configuration is split into two disjoint tiers (validated at load — no key may
appear in both):

- **App config** — `config/.env`, machine-local and gitignored. Copy the template:
  ```sh
  cp config/.env.template config/.env
  ```
- **Profile config** — `<profile-repo>/config/.profile`, committed inside each
  profile repo. Selected via the app config's `JOBJOB_PROFILE_*` registry +
  `JOBJOB_ACTIVE_PROFILE`.

### App config (`config/.env`)

| Variable | Purpose | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes |
| `CLAUDE_MODEL` | Model id (default: `claude-sonnet-4-6`) | No |
| `CLAUDE_CACHE_ENABLED` | Response-cache toggle (default: `true`) | No |
| `CACHE_DIR` | Local response-cache directory (default: `~/.cache/jobjob`) | No |
| `GOOGLE_CREDENTIALS_FILE` | Path to Google OAuth client-secrets JSON (default: `~/.config/jobjob/credentials.json`) | Drive/Sheets |
| `GOOGLE_TOKEN_FILE` | Path to pickled OAuth token (default: `~/.config/jobjob/token.pickle`) | Drive/Sheets |
| `APPLICATIONS_FOLDER_ID` | Applications-root Drive folder id | No |
| `APPLICATIONS_LOCAL_DIR` | Local synced Drive mirror | No |
| `DATA_DIR` | Input/output root (default: `data`) | No |
| `LINKEDIN_SHEET_ID` | Contacts spreadsheet id | `enrich` only |
| `JOBJOB_PROFILE_<NAME>` | Registry: path to a profile repo | Yes |
| `JOBJOB_ACTIVE_PROFILE` | Name of the active profile | Yes |

### Profile config (`<profile-repo>/config/.profile`)

| Variable | Purpose | Required |
|---|---|---|
| `RESUME_TEMPLATE_ID` | Resume-template Google Doc id for this profile | Drive only |
| `APPLICANT_NAME` | Your name as it appears on documents | No |
| `APPLICANT_PHONE` | Phone number for cover-letter header | No |
| `APPLICANT_EMAIL` | Email address for cover-letter header | No |
| `APPLICANT_LINKEDIN` | LinkedIn URL for cover-letter header | No |

### Google OAuth

`GOOGLE_CREDENTIALS_FILE` is a client-secrets JSON downloaded from the Google Cloud
Console for a project with the Drive API and Docs API enabled. First run opens a
browser to complete the OAuth flow and writes a pickled token to `GOOGLE_TOKEN_FILE`.
Subsequent runs reuse the token silently.

If you add new Google API scopes, delete `GOOGLE_TOKEN_FILE` to trigger re-auth:

```sh
rm ~/.config/jobjob/token.pickle
```

For step-by-step credential-acquisition instructions see
[docs/credentials-setup.md](credentials-setup.md).

---

## Static content

`static/content/` holds TOML files that drive resume customization:

| File | Purpose |
|---|---|
| `highlights.toml` | Credential blocks with keywords; the model selects the most relevant per JD |
| `skills.toml` | Skill entries with labels and keywords; used in the skills analysis |
| `templates.toml` | Resume archetypes (e.g. `leadership_biotech`) mapping keywords to Google Doc IDs |

`static/reference/` holds free-text documents the model reads as context:

| Path | Purpose |
|---|---|
| `background.*` | Career narrative and relocation intent |
| `cover_letters/` | Style-anchor examples (voice reference) |
| `stars/` | STAR-format experience blocks (honesty enforcement layer) |
| `writing_style.*` | Voice and writing rules |

Both directories are editable via the local webapp (`webapp/`). They serve as
fallbacks when no profile is active (e.g., tests or fresh clone). Do not store real
personal credentials here — these files are committed to the repo.

---

## Development

### Running tests

```sh
pdm run test                                           # unittest
pdm run ptest                                          # pytest
python -m unittest discover -t ./ -s tests/jobjob     # unittest (manual)
pytest                                                 # pytest (manual)
```

### Linting

```sh
pdm run lint    # ruff check .
```

### Code quality tools

```sh
pdm run init-hooks    # install pre-commit hooks
pdm run rm-hooks      # uninstall pre-commit hooks
pdm run clean         # remove __pycache__, .pyc, .pytest_cache
```

### Running the webapp (development mode)

See [webapp/README.md](../webapp/README.md). Two terminals required:

```sh
# Terminal 1 — backend
cd webapp/backend
uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — frontend dev server
cd webapp/frontend
npm run dev
```

---

## Architecture overview

| Module | Role |
|--------|------|
| `jobjob/config.py` | Central `Settings`; loads `config/.env` + builds applicant identity |
| `jobjob/ailib/` | AI orchestration: `query` (retry + cache), `client/` (provider adapters), `session.py` (cached context + token tracking) |
| `jobjob/loader/` | Auth, prompt/content/reference loaders, static-file location |
| `jobjob/structure/` | Typed domain models (job description, highlight, skill, …) |
| `jobjob/apply/` | Five-step application workflow: parse → highlights → resume → cover letter → skills |
| `jobjob/apply/generate/` | Individual AI-call steps |
| `jobjob/apply/output/` | PDF/DOCX output builders |
| `jobjob/enrich/` | LinkedIn profile ingestion into contacts sheet |
| `jobjob/gapi/` | Google Drive/Docs/Sheets I/O |
| `jobjob/__main__.py` | CLI dispatcher |

Adding a new AI provider: implement a thin adapter under `jobjob/ailib/client/`.

### Caching

- **Anthropic prompt cache** — stable context (resume, STARs, background, style
  examples) is sent as a cached system-message prefix shared across all five calls in
  a run. Cache lifetime is 5 minutes, extended by hits. Keep stable content at the top
  of the prefix; variable content (JD, company name) at the end.
- **Local file cache** — SHA256-keyed responses stored in `CACHE_DIR`. Skips
  identical prompts on re-runs. Toggle with `CLAUDE_CACHE_ENABLED`.
