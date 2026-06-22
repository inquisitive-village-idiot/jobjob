# Changelog

All notable changes to this project are documented here. Each entry is labeled by
the kind of change it represents — `[MAJOR]`, `[MINOR]`, or `[PATCH]` — following
[semantic versioning](https://semver.org/).

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
