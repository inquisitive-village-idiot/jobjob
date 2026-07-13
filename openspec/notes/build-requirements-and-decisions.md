# Build Requirements & Decisions (current state)

Synthesis of what **jobjob** currently is and the decisions behind it, as raw material
for `openspec/specs/`. Accurate to the shipped **2.8.0** codebase as of **2026-07-02**.

Format per capability: **Behavior** (what it does) · **Decisions** (why / the choice
made) · **Realized by** (traceability — paths, not requirements) · **Status / gaps**.
This is notes, not spec — see `README.md`.

Priority order for spec authoring (highest drift risk first):
`honesty-and-voice` → `config` → `apply-workflow`, then the rest.

---

## 1. Packaging & distribution

- **Behavior.** Installable Python package (`jobjob`), Python ≥ 3.12, distributed via
  pip/pipx and published to PyPI (currently 2.8.0). Two console scripts: `jobjob`
  (CLI) and `jobjob-app` (local webapp launcher + first-run setup wizard).
- **Decisions.** Trusted publishing (OIDC, no tokens); **production publish fires on a
  signed semver tag**, not a branch push, so docs/CI changes reach `main` without a
  near-identical wheel. `develop` → TestPyPI dev; `release/**` → TestPyPI staging.
- **Realized by.** `pyproject.toml`, `jobjob/__about__.py`, `.github/workflows/release.yml`,
  `jobjob/launcher.py`.
- **Status.** Stable. Optional extra `jobjob[autofill]` pulls Playwright (also powers
  the headless JD fetch).

## 2. CLI & dispatch

- **Behavior.** Single entrypoint `jobjob/__main__.py` dispatches sub-commands:
  `apply`, `enrich`, `auth`, `autofill`. Each sub-command owns its own arg parsing and
  is independently runnable (`python -m jobjob.apply`).
- **Decisions.** Thin dispatcher (`COMMANDS` mapping); batch processing is
  **continue-on-error** — one bad input logs and is skipped, the rest proceed.
- **Realized by.** `jobjob/__main__.py`, `jobjob/cli.py`, each `jobjob/<cmd>/__main__.py`.
- **Status.** Stable. (`enrich` is slated to be surfaced as **"Rolodex"** — issue #45.)

## 3. Configuration (two-tier, injected)

- **Behavior.** Two **disjoint** config tiers, validated at load (no key overlap):
  - **App config** `config/.env` (machine-local, gitignored; `.env.template` committed):
    `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL`, `CLAUDE_MODEL`, `CLAUDE_CACHE_ENABLED`,
    `CACHE_DIR`, `GOOGLE_CREDENTIALS_FILE`/`GOOGLE_TOKEN_FILE`,
    `APPLICATIONS_INPUT_DIR`/`APPLICATIONS_OUTPUT_DIR`/`APPLICATIONS_OUTPUT_DRIVE_ID`,
    `ENRICHMENT_INPUT_DIR`/`ENRICHMENT_OUTPUT_SHEET_ID`, `JOBJOB_PROFILE_<NAME>`/
    `JOBJOB_ACTIVE_PROFILE`.
  - **Profile config** `<profile>/config/.profile` (committed; no secrets, no local
    paths): `RESUME_TEMPLATE_ID`, `APPLICANT_NAME`/`_PHONE`/`_EMAIL`/`_LINKEDIN`,
    `INDUSTRY`, and resource-dir names `CONTENT_DIR`/`REFERENCE_DIR`/`PROMPT_DIR`.
- **Decisions.**
  - **Centralized but injected value-by-value** — `Settings` is built once at the
    entry point; feature functions take the concrete parameters they need, not a
    settings instance. (Directly from the original design brief.)
  - **Resolution priority:** CLI flag → env var → config file → built-in default.
  - **Backward-compatible renames:** deprecated keys (`DATA_DIR`,
    `APPLICATIONS_LOCAL_DIR`, `APPLICATIONS_FOLDER_ID`, `LINKEDIN_SHEET_ID`) are still
    read via load-time fallback and auto-migrated in `config/.env` — never a hard break.
  - **Env location:** `config/.env` (the original doc proposed `env/.env`; not adopted).
- **Realized by.** `jobjob/config.py` (`APP_KEYS`/`PROFILE_KEYS`, `load_settings`),
  `jobjob/migrate/`, `config/.env.template`.
- **Status.** Stable.

## 4. Profiles

- **Behavior.** A **profile** is a self-contained credential set: `content/*.toml` +
  `reference/` + `config/.profile`. A registry (env keys) lists profiles; one is
  active. The bundled **Tila Mer** example (`static/example/`) is read-only and doubles
  as the fallback when no profile is active. Users can create blank (from skeleton),
  duplicate, register an existing folder, or delete; a read-only save guard protects
  the example.
- **Decisions.** One unified profile model; profiles are git repos so credential
  content is versioned outside the app repo. Auto-migrate legacy `profile/` →
  `profiles/local/`.
- **Realized by.** `jobjob/loader/` (skeleton, location), `static/example/`,
  `webapp/backend/.../profiles`, `ProfilesPanel`.
- **Status.** Shipped. Lockable profiles = issue #29.

## 5. Content model (structured credentials)

- **Behavior.** Per-profile `content/*.toml`: **highlights** (context/text/keywords/
  enabled/topic), **skills** (label/text/keywords), **templates** (résumé templates +
  heading-anchored sections), **experience** (`Role`: company/title/location/start/end/
  current/description). `ExperienceSet.grouped()` groups *consecutive* same-employer
  roles (promotion = one block; a re-hire stays separate) while each role still fills
  as its own ATS row.
- **Decisions.** Structure-model pattern throughout: a **frozen dataclass** per item +
  a `*Set` collection with helpers + a `make_*` factory. Multi-role-at-one-employer is
  a flat list + adjacency grouping (not nested), because that is the shape an ATS wants.
- **Realized by.** `jobjob/structure/*.py`, `jobjob/loader/loadcontent.py`,
  `static/example/content/*.toml`.
- **Status.** Stable.

## 6. Reference docs & the honesty layer

- **Behavior.** Per-profile `reference/`: `background.*`, `writing_style.*`,
  `cover_letters/` (voice anchors), `stars/` (STAR docs). STAR docs are the **honesty
  enforcement layer** — generated claims must trace to them; an unsupported JD
  requirement is **flagged, not bridged**.
- **Decisions.** Credentials are never inferred; the gap is surfaced, not filled.
- **Realized by.** `jobjob/loader/loadreference.py`, `static/example/reference/`,
  and the prompt templates that consume them.
- **Status.** Stable. See §7-honesty in `honesty-and-voice` (highest-priority spec).

## 6b. Honesty & voice rules (product rules — spec first)

- **Behavior.** Every generated applicant-facing passage obeys: only true statements
  (trace to credentials/STAR); gaps by omission, surfaced in a deletable
  "⚠️ GAPS / FLAGS – DELETE BEFORE SENDING" block at the top, never inline; conservative
  geography; and voice rules (spaced en dash not em dash, no corporate-speak, no weak
  gerund openings, company-specific hook, 300–400 words / one page).
- **Decisions.** These are load-bearing and **must not relax between changes** — the
  primary reason for spec-capture.
- **Realized by.** `jobjob/prompts/*.txt` (cover letter / objective) + any mechanical
  validator. *Mechanical subset (en dash, length, gap-block format) should be extracted
  into code validators for real tests; judgment rules use eval/golden checks.*
- **Status.** Enforced via prompt today; exemplar spec drafted (see prior discussion).

## 7. AI client & providers

- **Behavior.** Thin adapter around a provider (`AnthropicAdapter`), fronted by an
  `AIClient` session. Supports `ANTHROPIC_BASE_URL` to point at a Claude-compatible
  proxy (e.g. a free Gemini-backed gateway).
- **Decisions.** Adapters are deliberately light so additional providers are easy;
  Anthropic is the only native one today.
- **Realized by.** `jobjob/ailib/client/anthropic.py`, `jobjob/ailib/session.py`,
  `jobjob/ailib/query.py`.
- **Status.** Native non-Anthropic (Gemini) adapter = issue #26.

## 8. Caching

- **Behavior.** (a) Anthropic **prompt caching** — stable context (résumé, STAR,
  cover-letter examples, background) sent as a cached system prefix reused across the
  five apply calls; (b) **local file cache** — SHA256-keyed responses under
  `~/.cache`, toggled by `CLAUDE_CACHE_ENABLED`.
- **Decisions.** Stable content stays at the top of the cached prefix and must not
  change between calls; variable content (JD, company) goes last.
- **Realized by.** `jobjob/ailib/query.py`, cache dir from config.
- **Status.** Stable.

## 9. Apply workflow

- **Behavior.** Five sequential AI calls sharing the cached prefix: JD parse →
  highlight selection → résumé update → cover-letter generation → skills/gap analysis.
  Output per application: a Google Doc résumé + cover letter + a résumé PDF, stored in a
  `YYYY-MM-DD - Company - Role` folder. **Reprocessing:** point at a JD copied into an
  output dir to regenerate in place, reusing the recorded Drive folder.
- **Decisions.** Section-aware résumé tailoring (heading-anchored; highlights placed
  verbatim). Output file naming is moving to `FirstLast_Type` (issue #47).
- **Realized by.** `jobjob/apply/`, `jobjob/gapi/`.
- **Status.** Stable; **GUI "Rerun" does not regenerate the docs — bug #46.**

## 10. JD ingestion & classification

- **Behavior.** A JD can enter as a PDF/dir, a **pasted** posting, or a **URL**. URL
  ingestion fetches + extracts (httpx + trafilatura) into a durable Markdown snapshot
  (records the source URL); when the cheap fetch is thin or fails and Playwright is
  present, it **falls back to a headless render** before extracting. A single input
  directory is classified as JD / LinkedIn profile / unsupported; unsupported logs an
  error and processing continues.
- **Decisions.** Snapshots are durable (survive the posting going 404) and fail loud;
  the source URL persisted in the snapshot is what `jobjob autofill` consumes.
- **Realized by.** `jobjob/ingest/jd_source.py`, `jobjob/classify/`.
- **Status.** Shipped; headless fetch new in 2.7.0. Not yet live-validated at scale.

## 11. Enrich / "Rolodex"

- **Behavior.** LinkedIn connection tracker (`enrich`): reads/writes a Google Sheets
  **contacts** tab with a fixed column contract
  (`location, company, role, name, linkedin_url, Request, 1st Msg, 2nd, 3rd,
  corporate_url, shared_connections, notes, last_verified, citations, found_by`);
  enrich also emits structured profile filenames + sidecar JSON + a dashboard table.
- **Decisions.** Reuses the shared loaders/AI/query layer; PDFs are the common input,
  vision only as fallback.
- **Realized by.** `jobjob/enrich/`, `ENRICHMENT_OUTPUT_SHEET_ID`.
- **Status.** Stable. **UI rename Enrich → Rolodex pending (#45)**; keep CLI/config
  back-compatible.

## 12. Autofill (assisted application filling)

- **Behavior.** `jobjob autofill <url>` opens a posting in a real, persistent-context
  browser and fills what it can from the active profile, then pauses for the human.
  **Assisted / human-in-the-loop — never auto-submits.** Adapter registry (first
  `matches` wins): Workday (also fills structured work history) → Greenhouse → Lever →
  Ashby → Workable → SmartRecruiters → **Generic fallback (must stay LAST)**. Anything
  not confidently mappable is **flagged, not invented**.
- **Decisions.** Fill from *our* structured data, not the ATS's résumé pre-fill. Named
  adapters share a `ContactFormAdapter` base (host regex + contact selector map).
  Selectors are best-effort per ATS and mirrored by local HTML fixtures — **no live
  sites in tests**; live-posting validation still owed.
- **Realized by.** `jobjob/autofill/` (runner, report, data, `adapters/*`),
  `tests/fixtures/*_application.html`. Optional extra `jobjob[autofill]`.
- **Status.** Shipped in 2.7.0 (Workday) / 2.8.0 (rest).

## 13. Résumé import

- **Behavior.** Upload a résumé → extract highlights, skills, objective, background,
  applicant identity, and **structured work history** → review/edit → save into the
  active profile's content. Multi-role-at-one-employer handled explicitly.
- **Decisions.** AI-assisted extraction with a mandatory review/confirm step before
  save (satisfies the original "send to AI, confirm before saving" ask).
- **Realized by.** `jobjob/ingest/resume_import.py`, `jobjob/ingest/save.py`,
  `webapp/.../ResumeImportPanel`.
- **Status.** Shipped.

## 14. Prompt customization

- **Behavior.** All prompts are `${name}` templates; a per-profile live editor + a
  Prompts page + `/api/prompts` let users edit them. `INDUSTRY` injects a domain hint
  into the objective prompt.
- **Decisions.** Prompts are committed, tracked artifacts — a prompt change that alters
  behavior should go through an OpenSpec change (anti-drift).
- **Realized by.** `jobjob/prompts/`, `jobjob/loader/loadprompt.py`, Prompts page.
- **Status.** Shipped (2.2.0).

## 15. Webapp (local dashboard)

- **Behavior.** FastAPI backend + React/TS frontend served by `jobjob-app`. Pages:
  Config, Static Content, Profiles, Prompts, Queue, Résumé import, About/Updates, plus
  a first-run setup wizard. Config is editable in the GUI **except secrets, which are
  never exposed**.
- **Decisions.** **Security-first:** filesystem path sandboxing, secrets never sent to
  the frontend, read-only guard on the example profile. Frontend lives in a separate
  dir using `jobjob` as a local package.
- **Realized by.** `webapp/backend/` (FastAPI, `security.py`), `webapp/frontend/`.
- **Status.** Shipped. **Queue gaps:** completed apply/enrich jobs + last-run info +
  a consolidated row-action dropdown = issue #44.

## 16. Status framework

- **Behavior.** A status SET plus a changelog/notes trail (auto-logged transitions +
  free-text notes) per application.
- **Realized by.** status module + webapp surface. **Status.** Shipped (notes trail 2.2.0).

## 17. Self-update

- **Behavior.** Config-page Updates panel checks PyPI on startup and performs an
  in-place `pipx`/`pip` upgrade.
- **Realized by.** self-update module + About/Updates panel. **Status.** Shipped.

## 18. Docs

- **Behavior.** Sphinx + reStructuredText under `docs/` (Guide / Library / REST API),
  published to GitHub Pages on `main`.
- **Realized by.** `docs/`, `.github/workflows/docs.yaml`. **Status.** Shipped.

---

## Cross-cutting engineering conventions

- Inject loggers (no module-level loggers); pre-compile regex; `pathlib` paths in/out
  (`.expanduser().resolve()`); **raise in low-level code**, catch/log/ignore only in
  primary processing loops; **`None` over `""`** in signatures (`x = x or default` at
  the top); prefer `collections.abc` over `typing`; frozen-dataclass + `*Set` + `make_*`
  factory for structured data; config injected at the entry point (feature modules
  don't read env).
- **Config injected value-by-value**, never a global settings object threaded through.
- **Tests:** `tests/jobjob/**` = `unittest` `TestCase` patterns (module aliased `MOD`,
  `ThisTestCase` base, one `TestCase` per unit, table-driven `subTest`, assert on error
  messages); `tests/webapp/**` = pytest (accepted exception); browser e2e marked `e2e`.
- **Formatting/lint:** black + isort + ruff (Python), prettier + eslint (frontend), via
  pre-commit.
- **gitflow:** `develop` default; squash-merge feature PRs to develop; release = bump
  `__about__.py` + `[release]` commit + signed semver tag pushed LAST (tag = publish
  trigger); `main` updated via a merge PR; never force-push `main`.

## Known inconsistencies to resolve while spec'ing

- **`None` vs `""`:** the convention says `None` over `""`, but some structured records
  (e.g. `Role` string fields) default to `""`. Decide and make consistent.
- **Config env location:** original design said `env/.env`; shipped as `config/.env`.
  Spec should assert the shipped location.

## Open issues (feed change proposals, not the baseline specs)

- #26 native Gemini adapter · #29 lockable profiles · #30 summary README ·
  #43 ATS résumé-compatibility check (structural first pass; keyword-fit follow-up) ·
  #44 queue completed-jobs + last-run + row-action dropdown · #45 Enrich → Rolodex ·
  #46 Rerun does not regenerate docs (bug) · #47 `FirstLast_Type` output file naming.

## Divergences from the original design docs (see `original/`)

- **Profiles, `experience.toml`, autofill, URL/headless ingestion, prompt
  customization, self-update, Sphinx docs, PyPI packaging** post-date the original docs
  entirely — they are current capabilities with no counterpart there.
- **Frontend #5 (conversational "discuss a file with AI")** was not built as chat; it
  was effectively superseded by the Prompts editor + résumé-import AI refine.
- **Frontend #3 tracking** is only partially met (see #44/#46).
