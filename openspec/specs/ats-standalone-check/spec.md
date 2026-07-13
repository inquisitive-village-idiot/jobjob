# ats-standalone-check Specification

## Purpose
TBD - created by archiving change ats-standalone-check. Update Purpose after archive.
## Requirements
### Requirement: Reassessment from saved artifacts, zero AI calls

The system SHALL rebuild the ATS assessment for a processed application from
its output directory alone: `JobDescription` from `summary.json`'s `job_info`
(via `from_mapping`), the skills mapping from `skills_analysis.json`, the
declared skill set via `load_skills`, and the rendered resume document via one
Google Docs read of `summary.json`'s `resume_id`. The reassessment MUST NOT
invoke any Anthropic API call.

#### Scenario: Re-check of a Drive-mode application

- **WHEN** a re-check runs on an output directory containing `summary.json`
  (with `job_info` and `resume_id`) and `skills_analysis.json`
- **THEN** it returns an `AtsAssessment` computed from the current resume Doc
- **AND** no AI-pipeline call is made

#### Scenario: Drive-skipped application

- **WHEN** the saved summary has no `resume_id`
- **THEN** the re-check returns a skipped assessment (no error)

#### Scenario: Missing artifacts

- **WHEN** `summary.json` or `skills_analysis.json` is absent
- **THEN** the re-check fails with an error naming the missing file

### Requirement: CLI subcommand

`jobjob ats <application-output-dir>` SHALL run the reassessment and print a
plain-text report to stdout containing: the coverage score, the
present / missing-evidenced / missing-unevidenced / unmapped buckets,
recommendations, skills-file candidates, up-skill targets, parseability
results, and fit-vs-ATS gaps. Exit code 0 on success (including a skipped
assessment); nonzero with a clear message on missing artifacts.

#### Scenario: Successful CLI re-check

- **WHEN** `jobjob ats <dir>` runs against a valid Drive-mode application dir
- **THEN** stdout contains the coverage score and each report section
- **AND** the exit code is 0

#### Scenario: CLI on a skipped application

- **WHEN** `jobjob ats <dir>` runs against a Drive-skipped application
- **THEN** stdout states the assessment was skipped and the exit code is 0

### Requirement: Webapp re-check endpoint

The backend SHALL expose `GET /api/tracking/applications/{folder_name}/ats`,
resolving the folder under the configured applications output directory and
returning the assessment as JSON (the `AtsAssessment` fields). Unknown folders
return 404; missing artifacts return a 4xx with a clear detail message.

#### Scenario: Endpoint returns the assessment

- **WHEN** the endpoint is called for a processed application folder
- **THEN** the response is 200 with coverage_score, buckets, recommendations,
  checks, and fit_gaps fields

#### Scenario: Unknown folder

- **WHEN** the endpoint is called with a folder that does not exist
- **THEN** the response is 404

