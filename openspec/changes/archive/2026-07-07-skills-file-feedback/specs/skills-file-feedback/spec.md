# Skills-File Feedback

## ADDED Requirements

### Requirement: Candidate aggregation across processed applications
The system SHALL aggregate skills-file candidates across processed application
directories, where a candidate is a skill that resolves to a canonical skill-cloud
entry, is evidenced in an application's saved skills analysis, and is not declared in
the active profile's skills file. Candidates MUST be deduplicated by canonical id and
carry evidence citations naming their source application directories. Aggregation MUST
use only saved artifacts (`summary.json`, `skills_analysis.json`), the packaged skill
cloud, and the loaded skills file — no AI calls and no Google API reads.

#### Scenario: Candidate evidenced in multiple applications
- **WHEN** the same undeclared canonical skill is evidenced in the skills analyses of
  two processed applications
- **THEN** the aggregation returns one candidate for that canonical id
- **AND** the candidate cites both source application directories with their evidence

#### Scenario: Declared skills are excluded
- **WHEN** an evidenced skill's canonical id is already declared in the active
  profile's skills file
- **THEN** it does not appear in the aggregated candidates

#### Scenario: Non-canonical and incomplete directories are skipped
- **WHEN** an evidenced skill does not resolve to a canonical skill-cloud entry, or a
  directory under the scan root lacks `summary.json` or `skills_analysis.json`
- **THEN** that skill or directory is skipped without failing the aggregation

### Requirement: Suggest command
The system SHALL provide a `jobjob skills suggest` command that prints the aggregated
candidates with their evidence citations. The scan root SHALL default to the
configured local applications mirror and be overridable via `--root`. The command
SHALL NOT modify any file unless `--apply` is given.

#### Scenario: Report without writes
- **WHEN** the user runs `jobjob skills suggest`
- **THEN** the aggregated candidates and evidence are printed
- **AND** the skills file is unchanged

#### Scenario: No candidates
- **WHEN** no processed application yields an undeclared evidenced canonical skill
- **THEN** the command reports that the skills file already covers the documented
  evidence and exits successfully

### Requirement: Confirmed append honoring the honesty gate
The system SHALL append entries to the active profile's skills file only for canonical
ids explicitly named via `--apply`, and only when every named id is in the current
aggregated candidate set. Appended entries MUST derive from the canonical cloud entry
(label = canonical id, text = display name, keywords = aliases) and the write MUST
preserve the existing file's formatting and comments. If any named id is unknown,
unevidenced, or already declared, the command SHALL abort without writing.

#### Scenario: Confirmed candidates are appended
- **WHEN** the user runs `jobjob skills suggest --apply <id>` with a valid candidate id
- **THEN** a skill entry derived from the canonical cloud entry is appended to the
  skills file
- **AND** existing entries, comments, and formatting are preserved

#### Scenario: Invalid id aborts the write
- **WHEN** any id passed to `--apply` is not in the aggregated candidate set
- **THEN** the command exits with an error naming the rejected id
- **AND** the skills file is unchanged

### Requirement: Suggestions endpoint
The webapp backend SHALL expose an endpoint returning the aggregated skills-file
suggestions as JSON, computed with the same aggregation rules as the CLI.

#### Scenario: Suggestions returned as JSON
- **WHEN** a client requests the skills suggestions endpoint
- **THEN** the response lists each candidate's canonical id, display name, and
  evidence citations

#### Scenario: Mirror not configured
- **WHEN** no local applications mirror is configured
- **THEN** the endpoint responds with an explanatory client error rather than an
  empty success
