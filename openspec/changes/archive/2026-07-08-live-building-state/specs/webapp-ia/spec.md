# Webapp Information Architecture

## ADDED Requirements

### Requirement: Live BUILDING state on application rows
An application row SHALL display a derived **BUILDING** indicator whenever a
document-generation run (`kind` build / batch / schedule) that matches the row
is currently `running`, regardless of which page/session launched it. The
indicator SHALL be derived from the merged run listing (never stored) and joined
to the row by the id-preferring rule (`entity_id`, falling back to folder name /
input path). A batch or schedule run SHALL mark **every** row it covers as
BUILDING. The Applications page SHALL refresh the run listing on a short interval
(≈5s, mirroring the Queue page) so BUILDING appears and clears without a manual
reload. BUILDING SHALL be display-only: on a built row it SHALL render as a badge
**next to** the user-editable status select and SHALL NOT replace the stored
status; the state filter SHALL gain a BUILDING chip when any row is building.

#### Scenario: Build started elsewhere shows BUILDING
- **WHEN** a build for an application is running (launched from a batch, a
  schedule, or another tab)
- **THEN** that application's row shows BUILDING within one refresh interval
- **AND** the badge does not replace the row's stored status

#### Scenario: Batch marks every covered row
- **WHEN** a build-all / batch run is running over several queued JDs
- **THEN** every covered row shows BUILDING for the duration of the batch

#### Scenario: BUILDING clears when the run ends
- **WHEN** a matching build run reaches a terminal state (completed/failed)
- **THEN** the row stops showing BUILDING on the next refresh
- **AND** a completed build's row reflects its built state
