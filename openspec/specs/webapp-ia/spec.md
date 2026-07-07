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
stored application status, with GENERATED displayed as BUILT). State SHALL be a
column with filter chips — never tabs. The existing insight chip, status editing,
and Company / Role fit / ATS coverage sorting apply to the table.

#### Scenario: Queued and built records in one table
- **WHEN** a JD is pending in the input directory and another application is built
- **THEN** both appear as rows in the same table, one QUEUED and one BUILT

#### Scenario: State filtering
- **WHEN** the user selects a state chip
- **THEN** only records in that state are shown

#### Scenario: GENERATED displays as BUILT
- **WHEN** a built application's stored status is GENERATED
- **THEN** the row displays BUILT
- **AND** the stored value is unchanged

### Requirement: Row actions dropdown with reserved Apply
Application row actions SHALL collapse into a per-row dropdown menu. QUEUED rows
offer Build and Delete; built rows offer Re-build, ATS, Notes, and Drive. The menu
SHALL include a disabled Apply action labeled as the future autofill step.

#### Scenario: Built row actions
- **WHEN** the user opens a built row's action menu
- **THEN** Re-build, ATS, Notes, and Drive are offered
- **AND** Apply is present but disabled, described as autofill to come

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

### Requirement: Build vocabulary in UI copy
UI copy SHALL name the document-generation pipeline Build and its re-run Re-build,
reserving Apply for the future autofill step. CLI commands, API routes, and stored
status values SHALL remain unchanged, and each rename site SHALL carry a breadcrumb
comment marking the deferred full rename.

#### Scenario: Launch actions say Build
- **WHEN** the user launches the pipeline for a queued JD or re-runs a built one
- **THEN** the controls read Build / Re-build rather than Apply / Re-run

