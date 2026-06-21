# Changelog

All notable changes to this project are documented here. Each entry is labeled by
the kind of change it represents — `[MAJOR]`, `[MINOR]`, or `[PATCH]` — following
[semantic versioning](https://semver.org/).

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
