# autofill-apply Specification

## Purpose
TBD - created by archiving change autofill-apply-wiring. Update Purpose after archive.
## Requirements
### Requirement: Launch assisted autofill from the webapp
The webapp SHALL launch the assisted autofill step for a built application as a
recorded background job. The launch endpoint SHALL resolve the application's
posting URL from its source tier (`source.json` `web_uri`) and SHALL reject the
request when no URL is present. Autofill SHALL run **detached from the request
worker** (its own process/session) so that a browser session left open for the
human never blocks a worker thread. The run SHALL be recorded in run history
with `kind: "apply"`, and the fill report SHALL be captured to the run log.

#### Scenario: Launch with a posting URL
- **WHEN** the user triggers Apply for a built application whose source has a
  `web_uri`
- **THEN** an autofill job starts, recorded in run history as `kind: "apply"`
- **AND** the launch does not block on the human finishing in the browser

#### Scenario: Launch without a posting URL is rejected
- **WHEN** Apply is triggered for an application whose source has no `web_uri`
- **THEN** the request is rejected and no job is started

#### Scenario: Fill report reaches the run log
- **WHEN** the autofill fill pass completes
- **THEN** the rendered fill report (fields filled vs. left for the human) is
  present in the run's log

### Requirement: Autofill hands the browser to the human without a terminal
The assisted autofill SHALL keep the browser window open for the human to finish
(custom widgets, screening questions, resume upload, submit) after the automated
fill, and SHALL do so without requiring a terminal/TTY when launched by the
webapp — waiting on the human closing the window rather than on stdin.

#### Scenario: Window stays open after fill, no TTY
- **WHEN** autofill is launched by the webapp (no controlling terminal) and the
  fill pass finishes
- **THEN** the browser window remains open for the human
- **AND** the process does not error waiting on stdin

