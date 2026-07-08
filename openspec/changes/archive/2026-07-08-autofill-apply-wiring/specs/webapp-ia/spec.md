# Webapp Information Architecture

## MODIFIED Requirements

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
