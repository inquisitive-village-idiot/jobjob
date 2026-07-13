# honesty-and-voice

## Purpose

Product rules governing every piece of generated applicant-facing text — cover letters
and the résumé objective. These rules are load-bearing: they protect the applicant from
untrue or defensive claims and enforce a consistent voice, and they must not relax
between changes. This capability is the highest-priority anti-drift target because the
behavior is enforced declaratively (via prompt templates) and can otherwise weaken
silently.

<!-- realized-by (traceability — not requirements):
     jobjob/prompts/*.txt        — cover-letter / objective generation (all rules)
     reference/stars/, content/*  — the credential sources claims must trace to
     TODO: extract the mechanical subset (en-dash, word count, gap-block format) into a
           validator so those scenarios are backed by deterministic tests.
     Judgment rules (hook, no corporate-speak) are checked via eval/golden review. -->

## Requirements

### Requirement: Claims trace to documented credentials

The system SHALL include only statements supported by the active profile's credential
content (highlights, STAR documents, background). A requirement with no supporting
credential SHALL be flagged rather than satisfied with an invented, inferred, or
bridged claim.

#### Scenario: Unsupported requirement is flagged, not fabricated

- **WHEN** a job description requires a credential absent from the profile's content
- **THEN** the requirement appears in the gap-flag block
- **AND** no sentence asserting that credential appears in the letter body

#### Scenario: A stated credential is used as written, not embellished

- **WHEN** the generated text references a documented credential
- **THEN** it does not add scope, metrics, titles, or dates beyond what the source states

### Requirement: Gaps are surfaced by omission in a deletable flag block

The system SHALL present detected gaps as a clearly-marked, deletable block at the TOP
of the cover letter, and SHALL NOT write defensive or disclaiming language about gaps
inline in the body.

#### Scenario: Gap block is present and correctly formatted

- **WHEN** one or more gaps are detected for a job description
- **THEN** the letter begins with a block headed `⚠️ GAPS / FLAGS – DELETE BEFORE SENDING`
- **AND** each gap is a bullet of the form `[Requirement]: [brief note]`
- **AND** the block is delimited so it can be removed in a single deletion

#### Scenario: The body contains no inline gap disclaimers

- **WHEN** a cover letter is generated
- **THEN** the body does not contain defensive statements about what the applicant has
  not done

### Requirement: Geography claims stay conservative

The system SHALL assert at most "open to relocation" regarding location, unless the role
explicitly requires a specific presence AND the profile's content supports that claim.

#### Scenario: No in-region presence asserted for a non-gated role

- **WHEN** a role does not explicitly require presence in a specific region
- **THEN** the generated text does not claim presence in that region

#### Scenario: Presence asserted only when required and supported

- **WHEN** a role explicitly requires presence in a region
- **AND** the profile's content supports that presence
- **THEN** the text may state it; **OTHERWISE** it states at most "open to relocation"

### Requirement: Mechanical voice formatting

The system SHALL apply the deterministic formatting rules to all generated text: spaced
en dashes (` – `) in place of em dashes, a capital letter after a colon that introduces
or clarifies a thought, and a total length of 300–400 words fitting one page.

#### Scenario: Em dashes are rendered as spaced en dashes

- **WHEN** generated text would contain an em dash
- **THEN** it is rendered as a spaced en dash ` – ` instead

#### Scenario: Length stays within one page

- **WHEN** a cover letter is generated
- **THEN** its body is between 300 and 400 words

### Requirement: Voice and framing

The system SHALL generate text that shows rather than announces, varies sentence
structure and word choice, avoids corporate-speak, avoids weak gerund openings, and
opens with a company-specific insight or hook rather than a self-description.

#### Scenario: Opening is a company hook, not a self-description

- **WHEN** a cover letter is generated
- **THEN** its first sentence references the company or role
- **AND** it does not open by describing the applicant

#### Scenario: No weak gerund opening

- **WHEN** a cover letter is generated
- **THEN** the opening sentence does not begin with a gerund phrase
  (e.g. "Translating complex challenges…")
