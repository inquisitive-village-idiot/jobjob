# Architecture

`jobjob` is a Python package (`jobjob/`) providing a CLI and a local webapp, plus a
bundled dashboard frontend.

## Package layout

- `jobjob/config.py` — central `Settings`, loaded from `config/.env` plus the active
  profile's `config/.profile`. Config is read once at the entry point and injected into
  the workflow; feature modules take plain parameters and never read the environment
  themselves.
- `jobjob/loader/` — auth, prompt/content/reference loaders, and static-file location.
  - `profiles.py` resolves the profile registry and the active profile.
  - `location.py` resolves `content`/`reference`/`prompt` against the active profile,
    falling back to the bundled `static/` defaults.
  - `loadcontent.py` loads highlights, skills, and templates from a profile's TOML.
  - `skeleton.py` writes a blank-but-valid profile for new users.
- `jobjob/ailib/` — `query` (retry + cache orchestration), `client/` (thin provider
  adapters, e.g. `anthropic.py`), `session.py` (`AIClient`: cached context + token
  usage), `cachemanager`.
- `jobjob/structure/` — typed domain models (job description, highlight, skill,
  template, …).
- `jobjob/apply/generate/` — the AI steps: parse, highlights, resume, cover letter,
  skills.
- `jobjob/apply/output/` — cover-letter PDF/DOCX builders.
- `jobjob/gapi/` — Google Drive/Docs I/O.
- `jobjob/apply/workflow.py` — orchestration; `jobjob/__main__.py` — the CLI entry.
- `jobjob/launcher.py` — the `jobjob-app` entry: scaffolds a working dir and serves the
  webapp.

Adding another AI provider is a single new adapter under `jobjob/ailib/client/`.

## How a run works

Five sequential Claude calls per application share a single cached context prefix
(resume, STAR examples, cover-letter examples, background):

1. **JD parse** — extract role level, domain, required skills, location, requirements.
2. **Highlight selection** — pick the most relevant credential blocks for the role.
3. **Resume update** — swap the objective and adjust emphasis on the Google Doc
   template via section-aware edits.
4. **Cover-letter generation** — assemble from the selected blocks, mirror JD language.
5. **Skills analysis** — gap check; flag anything not met or not honestly claimable.

## Caching

- **Anthropic prompt caching** — stable context is sent as a cached system prefix and
  reused across all five calls (ephemeral, ~5 min, extended by hits). Keep stable
  content at the top; variable content (JD, company) goes at the end.
- **Local file cache** — SHA256-keyed under `CACHE_DIR`, skips identical prompts on
  re-runs (`CLAUDE_CACHE_ENABLED`).

## Webapp

A local dashboard (`webapp/`: FastAPI backend + React frontend) manages the queue,
launches jobs, edits profile content, and reviews results. It binds to `127.0.0.1`
only and protects state-changing endpoints with a CSRF double-submit cookie. See
[../webapp/README.md](../webapp/README.md).
