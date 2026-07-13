# application-identity Specification

## Purpose
TBD - created by archiving change application-identity. Update Purpose after archive.
## Requirements
### Requirement: Stable entity id per application
Each application (and each contact) SHALL have a stable `entity_id` (a uuid4)
that persists across its whole lifecycle — the queued→built transition, folder
renames, and re-builds. The id SHALL be minted once, at first processing, and
stored as the entity tier's field in `metadata.json` (applications) or the
profile `.json` sidecar (contacts). A re-build of an existing entity folder
SHALL reuse the existing id, never mint a new one. Absence of an `entity_id`
SHALL be treated as a legacy record (see the id-preferring-join requirement) and
the id SHALL be minted lazily on the next natural write — no backfill or mirror
rewrite.

#### Scenario: First build mints and stores an id
- **WHEN** an application is built for a folder that has no `entity_id`
- **THEN** a uuid4 `entity_id` is written to the folder's `metadata.json`

#### Scenario: Re-build reuses the id
- **WHEN** an application whose folder already carries an `entity_id` is rebuilt
- **THEN** the existing `entity_id` is preserved unchanged

### Requirement: Source tier with parse-once fields
Each entity folder SHALL hold a `source.json` at its root recording the posting
itself: `file_uri` and/or `web_uri`, an `external_ref` (a JD-embedded
requisition id, stored as an attribute — never used as the key), and the
parse-once fields `company`, `role`, and `description`. The parse fields SHALL
be written once at first processing from the parsed job description; later
executions SHALL read them rather than rewrite them, so a re-build never
clobbers a user's corrections. `source.json` SHALL be read tolerantly (a
missing or malformed file degrades to legacy behavior, like `metadata.json`).

#### Scenario: source.json written once at first build
- **WHEN** an application is built and no `source.json` exists
- **THEN** a `source.json` is written with the entity id and the parsed company,
  role, description, and known URIs

#### Scenario: Re-build does not overwrite source fields
- **WHEN** an application with an existing `source.json` is rebuilt
- **THEN** the stored source fields are left unchanged

### Requirement: Editable source fields
The source fields `company`, `role`, `web_uri`, and `external_ref` SHALL be
user-editable to correct parse errors (attaching a posting URL to a PDF drop is
the motivating case). Editing SHALL update `source.json` in place without
touching analysis outputs or artifacts. The parse-once `description` and the
entity `entity_id` SHALL NOT be user-editable through this path.

#### Scenario: User corrects the company and attaches a URL
- **WHEN** the user edits an application's company and web URI
- **THEN** `source.json` reflects the new values
- **AND** the entity id and artifacts are unchanged

### Requirement: Cross-references prefer entity id with a name fallback
The system SHALL join an application across surfaces (run records to application
folders, and the rerun JD lookup) by preferring `entity_id` when both sides
carry one, and SHALL fall back to the folder name when either side lacks an id
(legacy). This preserves today's exact behavior for id-less records while making
id-bearing records survive folder renames.

#### Scenario: Id join survives a rename
- **WHEN** a run record and its application folder share an `entity_id` and the
  folder has since been renamed
- **THEN** the run still resolves to that application by id

#### Scenario: Legacy record joins by name
- **WHEN** either side of a join lacks an `entity_id`
- **THEN** the join falls back to matching on the folder name, as today

### Requirement: Contacts carry an entity id joinable from the sheet
A contact's `entity_id` SHALL be recorded in its profile `.json` sidecar and
written to an ID column on the contacts sheet, so a sheet row can be joined back
to its entity.

#### Scenario: Enriched contact gets an id in sidecar and sheet
- **WHEN** a profile is enriched and appended to the contacts sheet
- **THEN** its `entity_id` is present in the profile sidecar
- **AND** the same id appears in the sheet row's ID column

