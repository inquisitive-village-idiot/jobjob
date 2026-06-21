# Setup — Developer / Technical Reference

> **Not a developer?** See [docs/quickstart.md](quickstart.md) for a step-by-step
> guide written for non-technical users.

This document covers installation, environment configuration, and content setup for
anyone contributing to or maintaining jobjob.

---

## Prerequisites

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (recommended) or plain `pip`

## Install

```sh
uv sync              # recommended — creates the venv and installs dependencies
# — or —
pip install -e .     # installs the package in editable mode
```

## Upgrading

Installed copies upgrade like any pip/pipx/uv tool (`uv tool upgrade jobjob` /
`pipx upgrade jobjob`). On **2.0.0 and later** you can also update from the dashboard
(**Settings → Update**); that in-app updater is 2.0.0+ only.

**From 1.x:** the working-dir layout changed in 2.0.0 — a single `profile/` directory
became `profiles/<name>/`. On first launch, `jobjob-app` migrates `profile/` →
`profiles/local/` automatically (a directory move plus a registry-path rewrite;
idempotent, nothing lost). See the [Profiles guide](profiles.md).

## Environment configuration

Configuration is split into two disjoint tiers (validated at load — no key may
appear in both):

- **App config** — `config/.env`, machine-local and gitignored. Copy the template:
  ```sh
  cp config/.env.template config/.env
  ```
- **Profile config** — `<profile>/config/.profile`, inside each profile directory.
  Selected via the app config's `JOBJOB_PROFILE_*` registry + `JOBJOB_ACTIVE_PROFILE`.
  See the [Profiles guide](profiles.md) for the full profile model.

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
| `JOBJOB_PROFILE_<NAME>` | Registry: path to a profile directory | Yes |
| `JOBJOB_ACTIVE_PROFILE` | Name of the active profile | Yes |

### Profile config (`<profile>/config/.profile`)

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

## Profile content

Each profile's `content/` holds TOML files that drive resume customization:

| File | Purpose |
|---|---|
| `highlights.toml` | Credential blocks with keywords; the model selects the most relevant per JD |
| `skills.toml` | Skill entries with labels and keywords; used in the skills analysis |
| `templates.toml` | Resume archetypes (e.g. `print_correspondent`) mapping keywords to Google Doc IDs |

Each profile's `reference/` holds free-text documents the model reads as context:

| Path | Purpose |
|---|---|
| `background.*` | Career narrative and relocation intent |
| `cover_letters/` | Style-anchor examples (voice reference) |
| `stars/` | STAR-format experience blocks (honesty enforcement layer) |
| `writing_style.*` | Voice and writing rules |

Both directories are editable via the local webapp (`webapp/`). The repo's bundled
`static/content` and `static/reference` are the read-only **example** profile (the
fictional *Tila Mer*) and the fallback used when no profile is active (tests, a fresh
clone). Do not store real personal credentials in `static/` — it is committed to the
repo. See the [Profiles guide](profiles.md).

---

## Development

### Running tests

```sh
uv run --group test pytest               # full suite
uv run --group test pytest --no-cov      # skip coverage (faster)
```

### Linting

```sh
uv run ruff check .
```

### Docs

```sh
uv run --group docs sphinx-build -b html docs/source docs/build
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
