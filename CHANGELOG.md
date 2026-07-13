# Changelog

All notable changes to this project are documented here. Each entry is labeled by
the kind of change it represents — `[MAJOR]`, `[MINOR]`, or `[PATCH]` — following
[semantic versioning](https://semver.org/).

## [3.0.0] - 2026-07-13

- [MAJOR] **Breaking:** renamed the document-generation pipeline's CLI verb, HTTP routes, and stored vocabulary from "apply" to "build", completing the `webapp-restructure` UI-only rename: `jobjob apply` is now `jobjob build`; `jobjob apply` is repurposed to mean assisted auto-fill (formerly `jobjob autofill`, which is dropped as a subcommand); `/jobs/apply*` routes become `/jobs/build*`; the application status `GENERATED` becomes `BUILT` (legacy `GENERATED` values and folder-name prefixes are still read and normalized on the fly — no data is rewritten); run records now use `kind: "build"` for document generation (a one-time startup fixup migrates existing `kind: "apply"` records). Scripts or bookmarks against the old CLI verb or `/jobs/apply*` routes need updating
- [MINOR] Every application (and contact) folder now carries a stable identity, modeled as three tiers held together by one folder: an **entity** (`metadata.json` — a uuid `entity_id` minted once and reused across every re-build/rename, plus status and the notes changelog), a **source** (`source.json` — the posting's company/role/description and file/web/external reference, written once at first build; a re-build reads it back rather than overwriting it, so a manual correction via the new **Edit source** row action survives), and an **execution** (the current build's artifacts, with prior ones kept under `archive/<timestamp>/` on a re-build instead of being overwritten). A folder from before this change has neither field and keeps working exactly as it did — it joins by folder name, and gains an id lazily on its next build
- [MINOR] Manage an application's archived (superseded) executions from a new **Executions** panel: promote one back to primary (the current root is archived first, so nothing is ever lost mid-swap), leave a short note on why a run was kept, lock it against purge, and purge every unlocked archived execution for one application or, from a page-level button, across all of them at once
- [MINOR] Flag **possible duplicate applications** (normalized company + role match) with a badge and a panel to resolve them: **merge** re-parents the other application's current and archived executions into the survivor's history and unions its notes, or **delete** it outright; a new **Re-parse** row action re-runs JD parsing to pick up a parser/prompt improvement, deliberately overwriting the source fields written by an earlier build (with a confirmation, since this is the one sanctioned exception to parse-once)
- [MINOR] Every launched job (build, autofill, enrich, batch, schedule) now persists to disk as a run record with its log, under the applications input dir's new `runs/` folder — history (including failures) survives a backend restart instead of living only in memory; the Applications page shows a live **BUILDING** badge on a row whose latest matching run is still in progress, regardless of which page, batch, or schedule launched it
- [MINOR] Restructured dashboard navigation into **Applications / Contacts / Queue / Profiles**, with one filterable/sortable Applications table spanning both queued and built applications (state as filter chips, not tabs) and row actions collapsed into a dropdown
- [MINOR] The **Apply** row action on an Applications row launches assisted browser auto-fill for that application directly from the dashboard (gated on a posting URL being on file) — the fill report streams to the run's log like any other job
- [MINOR] Packaged a canonical, ESCO-seeded skill taxonomy jobjob now normalizes job-description and profile skills against, sharpening keyword matching over free-text skill names
- [MINOR] Résumé fit is now scored on two axes — a computed **role fit** (JD-skill coverage weighted by category) and a model-judged **preference fit** against your background — surfaced as a compact band + score in the résumé README and, per application, on the Dashboard
- [MINOR] Résumé output gets an **ATS assessment** (keyword coverage plus a parseability check) alongside fit scoring; re-check it any time without new AI calls via `jobjob ats <output_dir>` or the Dashboard's ATS report modal, and sort/filter applications by fit or ATS coverage
- [MINOR] `jobjob skills suggest` aggregates skill-file candidates evidenced across your processed applications but missing from your profile's `skills.toml`, with per-application evidence citations; `--apply <id>...` appends the confirmed ones in place
- [PATCH] Response cache entries are now keyed by `(model, prompt)` instead of prompt alone, so the same prompt under a different `CLAUDE_MODEL` no longer collides with — or wrongly hits — another model's cached response; existing prompt-only entries simply miss once and repopulate
- [PATCH] `metadata.json` and `summary.json` now stamp a `schema_version` on write, enabling future format migrations without touching existing files
- [PATCH] Cache-entry writes are now atomic (temp file + replace), preventing a truncated entry if a run is interrupted mid-write

## [2.8.0] - 2026-06-24

- [MINOR] Auto-fill now recognizes more application sites: dedicated adapters for Greenhouse, Lever, Ashby, Workable, and SmartRecruiters fill your name, email, phone, and LinkedIn from the active profile, and a generic fallback fills the contact basics on any other standards-compliant form (so `jobjob autofill <url>` does something useful even on an unrecognized board). Workday remains the one that also fills your structured work history. Selectors are best-effort per site; the résumé upload and submit are always left to you

## [2.7.0] - 2026-06-24

- [MINOR] Add `jobjob autofill <url>`: assisted, human-in-the-loop auto-fill of an online application in a real browser (Workday to start). It fills the contact basics and your work history from the active profile, flags anything it can't map confidently (custom date widgets, screening questions), and leaves account creation and the final submit to you — it never submits on your behalf. Needs the new browser extra (`pip install 'jobjob[autofill]'` then `playwright install chromium`)
- [MINOR] Store a structured work history per profile in `content/experience.toml` — one entry per role, keeping several roles at one employer as separate entries (the shape an application form wants) while still grouping them as one company on a résumé
- [MINOR] Résumé import now also extracts your work history into that structured form, with an editable Work-experience section in the import review before you save
- [MINOR] Ingest a job description from a JavaScript-rendered posting URL: when a plain fetch comes up empty (Workday, Greenhouse, LinkedIn and similar), jobjob falls back to a headless browser render before extracting, so more postings can be captured by URL instead of pasting. Uses the same browser extra
- [PATCH] Migrate the browser end-to-end test suite from Selenium to Playwright (no user-facing change): Playwright fetches its own Chromium, so the e2e CI job no longer needs a system Chrome, and the tests use auto-waiting locators

## [2.6.0] - 2026-06-24

- [MINOR] Add an `ANTHROPIC_BASE_URL` config option that points jobjob at a Claude-compatible proxy (e.g. one forwarding to a free Google AI / Gemini key), so it can run on a free experimental backend without a paid Anthropic key; settable on the Config page (AI section) or in `config/.env`, and documented in the new "Free option" guide

## [2.5.0] - 2026-06-23

- [MINOR] Restructure Settings into App, Profiles, and About sections; each profile is a tab (active first, example last) with a ＋ tab to add one by creating a blank profile, duplicating another, or registering an existing folder
- [MINOR] Profiles open as a clean read-only summary and switch to editable fields with Edit; a newly added profile loads its content immediately, without having to make it active first
- [MINOR] Move the app update controls into a new About section, alongside a "Report an issue" link
- [PATCH] Place the profile Edit toggle next to its fields (it was previously in the page header and easy to miss)
- [PATCH] Show the Response Cache setting as a true/false choice instead of a free-text box, and show each setting's default value in place of an empty box
- [PATCH] Add a close button and an Esc shortcut to the first-run setup wizard so it can be dismissed without completing it

## [2.4.0] - 2026-06-23

- [MINOR] Reorganize input/output settings per component: Applications (apply) and Enrichment (enrich) each have their own input directory and output, with the configuration grouped accordingly
- [MINOR] Resolve settings by priority — CLI flag, then environment variable, then config file, then built-in default — so an environment variable overrides the config file
- [PATCH] Rename the related config keys (`DATA_DIR`→`APPLICATIONS_INPUT_DIR`, `APPLICATIONS_LOCAL_DIR`→`APPLICATIONS_OUTPUT_DIR`, `APPLICATIONS_FOLDER_ID`→`APPLICATIONS_OUTPUT_DRIVE_ID`, `LINKEDIN_SHEET_ID`→`ENRICHMENT_OUTPUT_SHEET_ID`); the old names keep working and are auto-migrated in `config/.env` on launch — no action required
- [PATCH] Run versioned launch-time migrations (profile-layout and config-key rename) from a new internal migrations module

## [2.3.0] - 2026-06-23

- [MINOR] Redesign the Configuration page with a left sidebar: the App and per-profile tabs live in the sidebar, and the active tab expands to its subsections as scroll-spy anchors
- [MINOR] Extend the setup wizard with a Profile step: register an existing profile folder, or bootstrap a new one from a résumé (prefills your contact details and imports highlights/skills)
- [MINOR] Read applicant contact details (name/email/phone/LinkedIn) from a résumé during import
- [MINOR] Configure each profile's resource directory names (content/reference/prompt) from the new Directories settings group; the loaders fall back to the conventional names so existing profiles are unaffected
- [MINOR] Show a profile's on-disk location and a file-count pill for each resource directory on the Configuration page

## [2.2.2] - 2026-06-22

- [PATCH] Add a settings cog button in the header for quicker access to the configuration page (the account-menu Settings item remains)
- [PATCH] Restyle the configuration App/Profile switcher as underline tabs, matching the Static Content page
- [PATCH] Add a site footer with a copyright line and a "Report an issue" link
- [PATCH] Edit the configuration of any profile from per-profile tabs (not only the active one); the bundled example profile stays read-only, and the Profiles list shows separate Example/read-only pills with a left-aligned Switch action

## [2.2.1] - 2026-06-22

- [PATCH] Restore the app favicon and web manifest (they were referenced but not bundled, so the browser tab had no icon and every page load 404'd them)
- [PATCH] Clarify in the dashboard that application status and notes require a local applications mirror (`APPLICATIONS_LOCAL_DIR`)

## [2.2.0] - 2026-06-22

- [MINOR] Customize the AI prompts per profile from a new Prompts page: edit the résumé-objective, cover-letter, skills-analysis, and document-parsing prompts, with reset-to-default and a reference of the available `${variables}`
- [MINOR] Track each application's history: status changes are auto-logged with timestamps and you can add free-text notes, viewable from a Notes panel on the dashboard

## [2.1.1] - 2026-06-22

- [PATCH] Enforce formatting and linting in CI and pre-commit (black, isort, ruff for Python; prettier, eslint for the frontend) — no behavior change
- [PATCH] Tidy job-posting URL/paste ingestion: validate URLs with `httpx.URL`, make the fetch/length thresholds environment-overridable, and avoid creating unexpected directory trees
- [PATCH] Publish to PyPI on a release tag (with path gating) instead of on every push to `main`, so documentation- or tooling-only changes no longer require a version bump

## [2.1.0] - 2026-06-22

- [MINOR] Add an optional per-profile Industry / Domain setting (Settings → Profile) that is injected into the resume-objective prompt so the target company is described accurately for your field; neutral default when unset
- [PATCH] Model profile read-only/ownership as tracked state and isolate the bundled example profile under `static/example/` (no behavior change)

## [2.0.2] - 2026-06-21

- [PATCH] Internal code-quality cleanup (no behavior change): inject loggers through call chains instead of declaring module-level loggers, and pre-compile regular expressions as module-level constants

## [2.0.1] - 2026-06-21

- [PATCH] Refresh the README (accurate install/profiles, status badges) and the documentation guides
- [PATCH] Publish a Sphinx documentation site to GitHub Pages
- [PATCH] Add an "Upgrading from 1.x" note (the in-app updater requires 2.0.0+; the profile layout auto-migrates)

## [2.0.0] - 2026-06-20

- [MAJOR] Unify simple and advanced usage into one profile model
  - Local profile moves from <home>/profile/ to <home>/profiles/local/ (migrated automatically on first launch)
  - New installs scaffold a blank local profile instead of seeding the bundled example
- [MINOR] Add a read-only bundled "example" profile (Tila Mer) that can be duplicated
- [MINOR] Manage profiles from the Config page: create, duplicate, register, delete, switch
- [MINOR] Import an existing resume to bootstrap highlights, skills, and background
- [MINOR] Capture a job posting from a URL or pasted text
- [MINOR] Check for and apply app updates from the Settings page
- [MINOR] Per-topic and per-section resume output toggles, with copy-all

## [1.0.0]

- Initial public release.
