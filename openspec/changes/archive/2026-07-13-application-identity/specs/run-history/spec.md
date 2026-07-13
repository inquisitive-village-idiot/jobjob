# Run History

## ADDED Requirements

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
