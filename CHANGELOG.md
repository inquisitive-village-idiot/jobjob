# Changelog

All notable changes to this project are documented here. Each entry is labeled by
the kind of change it represents — `[MAJOR]`, `[MINOR]`, or `[PATCH]` — following
[semantic versioning](https://semver.org/).

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
