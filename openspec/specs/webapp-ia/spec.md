# webapp-ia Specification

## Purpose
TBD - created by archiving change webapp-restructure. Update Purpose after archive.
## Requirements
### Requirement: Entity and execution navigation
The webapp's primary navigation SHALL present Applications, Contacts, Queue, and
Profiles. Prompts SHALL be reachable from the account menu rather than the primary
navigation; Settings remains in the account menu / gear.

#### Scenario: Primary navigation
- **WHEN** the app loads
- **THEN** the primary nav shows Applications, Contacts, Queue, and Profiles
- **AND** Prompts opens from the account menu

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

### Requirement: Row actions dropdown with reserved Apply
Application row actions SHALL collapse into a per-row dropdown menu. QUEUED rows
offer Build and Delete; built rows offer Re-build, ATS, Notes, and Drive, plus
an **Apply** action for the assisted autofill step. Apply SHALL be **enabled
only when the application has a posting URL** (its source `web_uri`); otherwise
it SHALL be present but disabled, with a tooltip explaining that a posting URL
is required (attachable via source editing).

#### Scenario: Built row with a posting URL
- **WHEN** the user opens the action menu of a built row whose source has a URL
- **THEN** Re-build, ATS, Notes, Drive, and an enabled Apply are offered

#### Scenario: Built row without a posting URL
- **WHEN** the user opens the action menu of a built row with no posting URL
- **THEN** Apply is present but disabled, with a tooltip that a URL is required

#### Scenario: Queued row actions
- **WHEN** the user opens a QUEUED row's action menu
- **THEN** Build and Delete are offered

### Requirement: Failed runs surface on application records
An application record whose most recent matching run failed SHALL show a failure
chip that leads to the Queue page's run history.

#### Scenario: Failed build chip
- **WHEN** the latest run for a record failed
- **THEN** the record's row shows a failure chip
- **AND** following it reaches the run history

### Requirement: Queue page shows executions
The Queue page SHALL present executions: the persisted run history (each run
expandable to its stored log) and the existing scheduling controls. Pending input
files SHALL NOT be listed here — they are Applications/Contacts entities.

#### Scenario: Run history on the Queue page
- **WHEN** the user opens the Queue page after runs have executed
- **THEN** the runs list with kind, label, status, and timestamps
- **AND** a run expands to show its stored log

### Requirement: Contacts and Profiles pages
The Contacts page SHALL present the enrich domain: queued profile inputs with
Enrich / Enrich-all and the completed contacts table. The Profiles page SHALL
present the profile registry (registered profiles, active marker, switching) above
the active profile's content editors (highlights, skills, templates, reference,
resume import).

#### Scenario: Contacts page
- **WHEN** the user opens Contacts
- **THEN** queued profile inputs and completed contacts are shown with enrich
  actions

#### Scenario: Profiles page
- **WHEN** the user opens Profiles
- **THEN** the registry is shown with the active profile marked
- **AND** the content editors for the active profile follow

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

