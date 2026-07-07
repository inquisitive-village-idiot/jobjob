# Application Insights

## ADDED Requirements

### Requirement: Fit persisted machine-readably
The apply workflow SHALL persist a compact fit block in each application's
`summary.json` containing the qualitative band and the role-fit and preference-fit
scores. Axes that were not computable SHALL be persisted as null rather than omitted
or invented.

#### Scenario: Fit block written on apply
- **WHEN** an application is processed and the fit assessment yields band "Strong",
  role fit 0.72, and no preference fit
- **THEN** `summary.json` contains a fit block with band "Strong", role_fit 0.72, and
  preference_fit null

### Requirement: Completed listing exposes insights
The completed-applications listing SHALL include each application's persisted fit
block and ATS coverage when the local applications mirror is in use. Applications
whose `summary.json` is missing, unreadable, or predates fit persistence SHALL still
list, with the insight fields absent or null.

#### Scenario: Insights on listed applications
- **WHEN** the completed list is built from the local mirror and an application's
  `summary.json` holds a fit block and `ats_coverage`
- **THEN** the listing item carries those values

#### Scenario: Older application degrades gracefully
- **WHEN** an application's `summary.json` has no fit block
- **THEN** the application still appears in the listing without insight values

### Requirement: Dashboard insight chip and sorting
The Dashboard's completed-applications table SHALL show a compact per-row insight
chip (band plus available scores) and SHALL support ordering rows within each status
group by role fit or ATS coverage in addition to the default company ordering.
Rows without insight data SHALL show a placeholder and sort after scored rows.

#### Scenario: Chip rendered from insights
- **WHEN** a listed application has band "Strong", role fit 0.72, and ATS coverage
  0.64
- **THEN** its row shows a chip presenting the band and the two scores

#### Scenario: Sorting by fit
- **WHEN** the user selects fit ordering
- **THEN** rows within each status group order by role fit descending, rows without
  a score last

### Requirement: ATS report view with re-check
The Dashboard SHALL provide a per-application ATS report view backed by the existing
standalone re-check endpoint, rendering the assessment sections and offering a
re-check action that re-runs the assessment without re-running the apply pipeline.
When the endpoint reports that the saved artifacts cannot support a re-check, the
view SHALL surface that explanation.

#### Scenario: Report fetched on open
- **WHEN** the user opens an application's ATS report
- **THEN** the current assessment is fetched from the re-check endpoint and its
  sections are rendered

#### Scenario: Re-check after editing the resume
- **WHEN** the user activates re-check
- **THEN** the assessment is fetched again and the view updates

#### Scenario: Pre-ATS application
- **WHEN** the endpoint responds that the saved artifacts are missing or invalid
- **THEN** the view shows the endpoint's explanation instead of a report
