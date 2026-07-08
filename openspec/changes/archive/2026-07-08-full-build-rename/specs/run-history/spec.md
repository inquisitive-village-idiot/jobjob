# Run History

## ADDED Requirements

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
