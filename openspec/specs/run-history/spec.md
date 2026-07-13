# run-history Specification

## Purpose
TBD - created by archiving change webapp-restructure. Update Purpose after archive.
## Requirements
### Requirement: Runs persist with their logs
Every job launched through the webapp SHALL be recorded on disk with its kind,
label, target paths, folder name (when known), status, error, timestamps, and the
full log output, so that runs — especially failures — remain inspectable after the
backend restarts. Persistence failures SHALL be logged and MUST NOT fail the job
itself.

#### Scenario: Failed build survives a restart
- **WHEN** a build run fails and the backend restarts
- **THEN** the run still lists with status failed and its error
- **AND** its full log remains retrievable

#### Scenario: Record written at start and completion
- **WHEN** a job is launched
- **THEN** a run record exists with status running
- **AND** on completion the record carries the final status and finished timestamp

### Requirement: Run listing and log retrieval
The backend SHALL expose the merged run history — live in-memory jobs joined with
persisted records, newest first — and the stored log text of any persisted run. A
persisted record still marked running with no live counterpart SHALL be reported as
failed (interrupted).

#### Scenario: Merged listing
- **WHEN** a client lists runs while one job is live and older persisted runs exist
- **THEN** the response contains the live job and the persisted runs, newest first,
  each with kind, label, status, and timestamps

#### Scenario: Stored log retrieval
- **WHEN** a client requests a persisted run's log
- **THEN** the stored log text is returned

#### Scenario: Interrupted run reported as failed
- **WHEN** a persisted record says running but no live job with that id exists
- **THEN** the listing reports that run as failed

### Requirement: Run retention
The run store SHALL prune itself to a bounded number of most-recent records
(with their logs) so history does not grow without limit.

#### Scenario: Old runs pruned
- **WHEN** a new run is recorded and the store exceeds the retention bound
- **THEN** the oldest records and their log files beyond the bound are removed

### Requirement: Document-generation runs use the build kind
Run records for the document-generation pipeline SHALL store `kind: "build"`.
The `apply` kind is reserved for the autofill step. On startup the backend SHALL
perform a one-time, marker-guarded fixup that rewrites any legacy
`kind: "apply"` document-generation records in the runs directory to
`kind: "build"`, running exactly once so that autofill runs recorded as
`kind: "apply"` in the future are never rewritten.

#### Scenario: New build run records the build kind
- **WHEN** a document-generation job is launched through the webapp
- **THEN** its run record stores `kind: "build"`

#### Scenario: Legacy apply records are fixed up once
- **WHEN** the backend starts and the runs directory holds legacy
  `kind: "apply"` records and no migration marker
- **THEN** those records are rewritten to `kind: "build"`
- **AND** the migration marker is written so the fixup does not run again
- **AND** records created afterward with `kind: "apply"` are left untouched

### Requirement: Run records carry the entity id
A run record SHALL carry the `entity_id` of the application (or contact) it
processed, so runs join to their entity by id rather than only by folder name.
Because the id is minted during the build, the record MAY be stamped with the
id when the run finishes rather than when it starts. A run whose entity has no
id (legacy) SHALL simply omit the field, joining by name as before.

#### Scenario: Finished build run records its entity id
- **WHEN** a build run completes for an application with an `entity_id`
- **THEN** its run record carries that `entity_id`

#### Scenario: Legacy run omits the id
- **WHEN** a run processes an application that has no `entity_id`
- **THEN** the run record omits `entity_id` and remains joinable by folder name

