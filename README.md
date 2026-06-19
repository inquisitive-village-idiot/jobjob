# `jobjob`

Generate tailored resumes and cover letters at scale. Given a job-description PDF,
`jobjob` runs five sequential Claude calls (sharing one cached context prefix) to parse
the role, select credential highlights, generate a cover letter, and produce a skills
gap analysis — writing local artifacts and (optionally) uploading to Google Drive.

> **New here?** If you have never used a terminal before, start with the
> [Quick-Start Guide](docs/quickstart.md) — it walks through every step.

## Install

```sh
pdm install            # or: pip install -e .
```

Requires Python ≥ 3.12.

## Configuration

Configuration is split into two **disjoint** tiers (no overlap, validated at load):

- **App config** — `config/.env`, machine-local and **gitignored** (only
  `config/.env.template` is committed). One jobjob instance: secrets, local paths,
  output IDs, and the *profile registry*.
- **Profile config** — `<profile-repo>/config/.profile`, committed inside each
  profile repo. The active profile's applicant identity and resume template.

```sh
cp config/.env.template config/.env
# then edit config/.env with your values (incl. a JOBJOB_PROFILE_* registry entry)
```

A **profile** is a separate git repo of content jobjob tailors from (`content/`,
`reference/`, `config/.profile`, optional `prompt/`). The app config registers
profiles by path and selects the active one; switch profiles to swap the whole
content set (e.g. one content set per role type). See
[docs/setup.md](docs/setup.md) for the full reference.

| Variable | Tier | Purpose | Required |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | app | Anthropic API key | Yes |
| `GOOGLE_CREDENTIALS_FILE` / `GOOGLE_TOKEN_FILE` | app | Google OAuth | Drive/Sheets only |
| `APPLICATIONS_FOLDER_ID` | app | Applications-root Drive folder id | No |
| `APPLICATIONS_LOCAL_DIR` | app | Synced Drive mirror (local) | No |
| `LINKEDIN_SHEET_ID` | app | Contacts spreadsheet id (enrich) | `enrich` only |
| `JOBJOB_PROFILE_<NAME>` / `JOBJOB_ACTIVE_PROFILE` | app | Profile registry + active | Yes |
| `RESUME_TEMPLATE_ID` | profile | Resume-template Google Doc id | Drive only |
| `APPLICANT_NAME` / `_PHONE` / `_EMAIL` / `_LINKEDIN` | profile | Cover-letter header | No |

Config is read once at the entry point and injected into the workflow; feature modules
take plain parameters and never read the environment themselves.

For obtaining API keys and Google OAuth credentials, see
[docs/credentials-setup.md](docs/credentials-setup.md).

## Usage

```sh
# Generate a resume + cover letter for a job-description PDF:
jobjob apply path/to/job_description.pdf          # full run (Drive + local)
jobjob apply path/to/job_description.pdf --skip-drive -o ./out  # local only

# Import a LinkedIn profile screenshot into the contacts sheet:
jobjob enrich path/to/profile.pdf
jobjob enrich path/to/profile.pdf --dry-run       # parse only, no sheet write
```

See [docs/usage.md](docs/usage.md) for the full flag reference and examples.

**Local output** (`-o <dir>`, default `./out/<date> - <Company> - <Role>/`): cover
letter (`.pdf`/`.docx`), `skills_analysis.json`, a copy of the JD, the resume PDF,
and `summary.json`.

**Google Drive folder** (`YYYY-MM-DD - Company - Role`) holds exactly four artifacts:
the README (Google Doc), the JD PDF, the customized resume (Google Doc), and the cover
letter (Google Doc).

## Resume templates

The active profile's `content/templates.toml` defines resume variations by archetype
(e.g. `leadership_biotech`, `leadership_research`), each with a Google Doc `doc_id` and
keywords/description. The workflow uses `--template <name>` if given, otherwise asks
the model to classify the JD against the archetypes. With no `templates.toml`, a single
`RESUME_TEMPLATE_ID` is used as the default. (The repo's `static/content` ships defaults
used when no profile is active — e.g. tests and a fresh clone.) See
[docs/usage.md](docs/usage.md) for the `--template` flag.

## Architecture

- `jobjob/config.py` — central `Settings`, loaded from `config/.env` + the active
  profile's `config/.profile`; `jobjob/loader/profiles.py` resolves the registry.
- `jobjob/ailib/` — `query` (retry + cache orchestration), `client/` (thin provider
  adapters; `anthropic.py`), `session.py` (`AIClient`: cached context + token usage),
  `cachemanager`.
- `jobjob/loader/` — auth, prompt/content/reference loaders, static-file location.
- `jobjob/structure/` — typed domain models (job description, highlight, skill, …).
- `jobjob/apply/generate/` — the AI steps (parse, highlights, resume, cover letter,
  skills).
- `jobjob/apply/output/` — cover-letter PDF/DOCX builders.
- `jobjob/gapi/` — Google Drive/Docs I/O.
- `jobjob/apply/workflow.py` — orchestration; `jobjob/__main__.py` — CLI.

Adding another AI provider is a single new adapter under `jobjob/ailib/client/`.

## Webapp

A local dashboard for managing the queue, launching jobs, and reviewing results is in
`webapp/`. See [webapp/README.md](webapp/README.md) for setup and usage.

## Development

```sh
pdm run python -m unittest discover -t ./ -s tests/jobjob   # or: pytest
```
