# Webapp Information Architecture

## MODIFIED Requirements

### Requirement: Unified Applications table
The Applications page SHALL present all application records in one
filterable/sortable table drawing from both sources: pending JDs from the input
directory (state QUEUED) and built applications from the output mirror (their
stored application status BUILT by default). State SHALL be a column with filter
chips — never tabs. The existing insight chip, status editing, and Company /
Role fit / ATS coverage sorting apply to the table.

#### Scenario: Queued and built records in one table
- **WHEN** a JD is pending in the input directory and another application is built
- **THEN** both appear as rows in the same table, one QUEUED and one BUILT

#### Scenario: State filtering
- **WHEN** the user selects a state chip
- **THEN** only records in that state are shown

#### Scenario: Legacy GENERATED normalizes to BUILT
- **WHEN** an application's stored status is the legacy value GENERATED
- **THEN** it is read as BUILT and the row displays BUILT
- **AND** the old file on the Drive mirror is not rewritten in place

## ADDED Requirements

### Requirement: Build vocabulary end to end
The document-generation pipeline SHALL be named **Build** (its re-run
**Re-build**) consistently across UI copy, CLI commands, HTTP API routes, and
stored values, with **Apply** reserved for the autofill step. The CLI
document-generation command SHALL be `jobjob build`; the API routes SHALL be
`/jobs/build`, `/jobs/build/rerun`, `/jobs/build/from-url`,
`/jobs/build/from-text`, and `/jobs/build-all`; document-generation run records
SHALL store `kind: "build"`; and the default application status SHALL be
`BUILT`. No `UI-only rename` breadcrumb comments SHALL remain.

#### Scenario: Launch actions say Build
- **WHEN** the user launches the pipeline for a queued JD or re-runs a built one
- **THEN** the controls read Build / Re-build rather than Apply / Re-run

#### Scenario: Surfaces agree on Build
- **WHEN** the CLI, an API route, or a stored run/metadata value names the
  document-generation pipeline
- **THEN** it uses Build / build / BUILT vocabulary, not Apply / apply / GENERATED

### Requirement: Application metadata schema versioning
Application `metadata.json` files SHALL carry an integer `schema_version` that
is decoupled from the app version and increments only on format changes. A file
with no `schema_version` SHALL be treated as version 0. Reads SHALL apply a
version-keyed migration bringing an older file up to the current schema before
the value is used, without rewriting the source file; writes SHALL stamp the
current version. The GENERATED→BUILT status rename SHALL be implemented as this
read migration (files below the current version have `status: "GENERATED"`
normalized to `"BUILT"`).

#### Scenario: Unstamped legacy file is version 0 and migrates on read
- **WHEN** a metadata file has no `schema_version` and `status: "GENERATED"`
- **THEN** it is read as the current schema with `status: "BUILT"`
- **AND** the source file is unchanged until the next write

#### Scenario: Write stamps the current version
- **WHEN** the app writes a metadata file
- **THEN** the file carries the current `schema_version`
- **AND** its status vocabulary is BUILT, never GENERATED

### Requirement: Legacy folder-name status prefix accepts both words
The application folder-name status-prefix parser SHALL accept a legacy
`GENERATED` prefix in addition to the current status words and SHALL normalize a
matched `GENERATED` prefix to `BUILT`, so legacy folder names still resolve.

#### Scenario: Legacy GENERATED-prefixed folder resolves
- **WHEN** an application folder name begins with the legacy prefix `GENERATED`
- **THEN** the parser strips the prefix and resolves the status as BUILT

## REMOVED Requirements

### Requirement: Build vocabulary in UI copy
**Reason**: Superseded by "Build vocabulary end to end" — the rename is no
longer UI-copy-only; CLI, API, and stored values now use Build vocabulary and
the breadcrumb comments are removed.
