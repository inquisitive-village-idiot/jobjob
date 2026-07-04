# ATS Assessment

## ADDED Requirements

### Requirement: Coverage scoring against the rendered resume

The system SHALL score the updated resume document's text against the JD's
canonical skills, classifying each canonical requirement as `present` (name or
alias found, case-insensitive, word-boundary), `missing-evidenced` (absent but
supported in the skills analysis), or `missing-unevidenced` (absent and
unsupported). The coverage score SHALL be deterministic for a given resume text,
skills mapping, and cloud version. UNMAPPED requirements are listed but excluded
from the score.

#### Scenario: Skill present via alias

- **WHEN** a canonical JD skill's alias appears in the resume text
- **THEN** that requirement is classified `present`

#### Scenario: Evidenced skill missing from resume

- **WHEN** a canonical JD skill is absent from the resume text but classified as
  supported in the skills analysis
- **THEN** it is classified `missing-evidenced`

#### Scenario: Deterministic score

- **WHEN** the same resume text, skills mapping, and cloud are scored twice
- **THEN** the coverage score and all classifications are identical

### Requirement: Recommendations are evidence- and skills-file-bounded

Fix recommendations SHALL be derived only from the `missing-evidenced` bucket AND
only for skills that resolve to an entry in the user's skills file
(`content/skills.toml`) — the declared skill set is the allowlist. Each
recommendation MUST cite the evidence supporting the skill. The system MUST NOT
recommend adding any skill lacking documented evidence or absent from the skills
file, and MUST NOT generate resume copy — recommendations state the gap and its
evidence.

#### Scenario: Recommendation cites evidence

- **WHEN** a recommendation is produced for a missing-evidenced skill present in
  the user's skills file
- **THEN** it names the skill and the supporting evidence from the skills analysis

#### Scenario: Unevidenced skills are never recommended

- **WHEN** a JD skill is `missing-unevidenced`
- **THEN** no recommendation is produced for it
- **AND** it is listed as a gap, not a fix

#### Scenario: Evidenced but undeclared skill becomes a skills-file candidate

- **WHEN** a JD skill is evidenced in the skills analysis but does not resolve to
  any entry in the user's skills file
- **THEN** no fix recommendation is produced for it
- **AND** it is surfaced in the README as a skills-file candidate ("consider
  adding to your skills file")

### Requirement: Up-skill targets are surfaced but never used in generation

`missing-unevidenced` skills SHALL be listed in the README as possible up-skill
targets for the user. These skills MUST NOT flow into resume or cover-letter
generation in any form.

#### Scenario: Up-skill targets listed

- **WHEN** the README is generated and missing-unevidenced skills exist
- **THEN** they appear in an up-skill targets list in the ATS section

#### Scenario: Up-skill targets excluded from generation

- **WHEN** resume and cover-letter content is generated for the application
- **THEN** missing-unevidenced skills contribute nothing to either document

### Requirement: Parseability checks on document structure

The system SHALL run a named set of structural checks on the updated resume
document (content in tables, non-standard section headings, images/text boxes,
multi-column layout), each returning pass or warn with a one-line reason. Check
thresholds and the check set SHALL be defined as documented, tunable constants in
a single module.

#### Scenario: Table content warning

- **WHEN** the resume document places body content inside a table
- **THEN** the parseability results include a warning naming the check and reason

#### Scenario: Clean document passes

- **WHEN** the resume document contains none of the flagged structures
- **THEN** all parseability checks report pass

### Requirement: README renders the ATS assessment

The application README SHALL include an "ATS assessment" section: the coverage
score with per-bucket skill lists, parseability results, and recommendations.
When role-fit data is available, the section SHALL also list fit-vs-ATS gaps
(skills strong on the fit axis but absent from the resume text). If the resume
document is unavailable (Drive skipped), the section SHALL state that and render
nothing else.

#### Scenario: Full assessment rendered

- **WHEN** the README is generated after a successful resume update
- **THEN** the DOCX contains coverage score, bucket lists, parseability results,
  and evidence-cited recommendations

#### Scenario: Drive skipped

- **WHEN** no resume document was generated
- **THEN** the ATS section states the assessment was skipped and includes no score
