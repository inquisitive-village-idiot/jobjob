# Setup & configuration

Two ways to configure jobjob: the **in-app wizard** (easiest) or **editing the config
files** by hand (advanced). They're interchangeable — use whichever you prefer.

## The wizard (recommended)

Launch jobjob in a terminal (macOS/Linux) or PowerShell (Windows):

```
jobjob-app
```

The first run creates your jobjob folder (`~/Documents/jobjob`) and opens the dashboard.
A **Setup** window opens automatically (reopen anytime from the **account menu → Run
setup**) and walks you through:

1. **Anthropic API key** — paste your key (see [Getting started](quickstart.md), Step 1).
   *Done when:* "✓ A key is configured."
2. **Google (optional)** — **upload** the `credentials.json` from
   [Set up Google Drive/Docs](install-google-project.md), then **Connect Google** and
   approve in the tab that opens. *Done when:* "✓ Google is connected."
3. **Profile** — optionally register an existing profile folder or bootstrap one from a
   résumé. See [Profiles](profiles.md).
4. **Your details** — name, email, phone, LinkedIn (cover-letter header).

Change anything later under **Settings**.

---

## Editing config files (advanced)

jobjob has **two config files**, validated as disjoint (no key may appear in both):

- **App config** — `<jobjob folder>/config/.env` (machine-local; default folder
  `~/Documents/jobjob`).
- **Profile config** — `<profile>/config/.profile`, inside each profile directory (see
  [Profiles](profiles.md)).

**Open the app config** in any plain-text editor:

- **macOS:** `open -e ~/Documents/jobjob/config/.env`
- **Linux:** `nano ~/Documents/jobjob/config/.env`
- **Windows (PowerShell):** `notepad $env:USERPROFILE\Documents\jobjob\config\.env`

Lines are `KEY="value"` — keep the quotes, no spaces around `=`.

### App config keys (`config/.env`)

**AI (required)**

| Variable | Purpose | Required |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic API key (a secret — the wizard/Settings won't display it) | Yes |
| `CLAUDE_MODEL` | Model id (default: `claude-sonnet-4-6`) | No |
| `CLAUDE_CACHE_ENABLED` / `CACHE_DIR` | Response-cache toggle / directory | No |

**Google (for Drive/Docs output)**

| Variable | Purpose | Required |
|---|---|---|
| `GOOGLE_CREDENTIALS_FILE` | Path to the OAuth client-secrets JSON (default: `~/.config/jobjob/credentials.json`) | Drive/Sheets |
| `GOOGLE_TOKEN_FILE` | Path to the pickled OAuth token (default: `~/.config/jobjob/token.pickle`) | Drive/Sheets |

**[Applications](usage-applications.md) (apply)**

| Variable | Purpose | Required |
|---|---|---|
| `APPLICATIONS_INPUT_DIR` | Input/working root holding `jobs/`, `profiles/`, `completed/` (default: `data`) | No |
| `APPLICATIONS_OUTPUT_DIR` | Local synced Google Drive mirror (output) | No |
| `APPLICATIONS_OUTPUT_DRIVE_ID` | Drive folder id for output | No |

**[Enrichment](usage-enrichment.md) (enrich)**

| Variable | Purpose | Required |
|---|---|---|
| `ENRICHMENT_INPUT_DIR` | Enrich input root; blank ⇒ use `APPLICATIONS_INPUT_DIR` | No |
| `ENRICHMENT_OUTPUT_SHEET_ID` | Contacts spreadsheet id | `enrich` only |

**Profile registry**

| Variable | Purpose | Required |
|---|---|---|
| `JOBJOB_PROFILE_<NAME>` | Path to a profile directory | Yes |
| `JOBJOB_ACTIVE_PROFILE` | Name of the active profile | Yes |

### Profile config keys (`<profile>/config/.profile`)

| Variable | Purpose | Required |
|---|---|---|
| `APPLICANT_NAME` / `_PHONE` / `_EMAIL` / `_LINKEDIN` | Cover-letter header details | No |
| `RESUME_TEMPLATE_ID` | Résumé-template Google Doc id for this profile | Drive only |
| `INDUSTRY` | Optional domain (e.g. "science journalism") used to describe the target company accurately | No |

### Where profile content lives

A profile is a directory (default `<jobjob folder>/profiles/<name>/`). Alongside its
`config/.profile`, it holds the documents jobjob tailors from:

- `content/*.toml` — `highlights.toml`, `skills.toml`, `templates.toml` (your
  credential blocks, skills, and résumé archetypes).
- `reference/` — free-text context the AI reads: `background.*`, `writing_style.*`,
  `cover_letters/`, `stars/`.

Edit these in the browser from the **Static Content** tab, or register a profile that
points at an existing folder. See [Profiles](profiles.md).

### Precedence & deprecated keys

Highest first: **CLI flag → environment variable → config file → built-in default.** An
environment variable overrides the config file, even across the rename below; within one
source, the new name wins over its deprecated alias.

Pre-2.4 names are still read and auto-rewritten in `config/.env` on launch — no action
needed:

| Deprecated | New name |
|---|---|
| `DATA_DIR` | `APPLICATIONS_INPUT_DIR` |
| `APPLICATIONS_LOCAL_DIR` | `APPLICATIONS_OUTPUT_DIR` |
| `APPLICATIONS_FOLDER_ID` | `APPLICATIONS_OUTPUT_DRIVE_ID` |
| `LINKEDIN_SHEET_ID` | `ENRICHMENT_OUTPUT_SHEET_ID` |

### Place the Google credentials file

If you set up the [Google project](install-google-project.md), put the downloaded JSON
where jobjob expects it (or point `GOOGLE_CREDENTIALS_FILE` at its full path):

- **macOS/Linux:**
  ```sh
  mkdir -p ~/.config/jobjob
  cp ~/Downloads/client_secret_*.json ~/.config/jobjob/credentials.json
  ```
- **Windows (PowerShell):**
  ```powershell
  mkdir $env:USERPROFILE\.config\jobjob -Force
  copy $env:USERPROFILE\Downloads\client_secret_*.json $env:USERPROFILE\.config\jobjob\credentials.json
  ```

The first Drive/Docs run opens a browser to authorize and writes the token to
`GOOGLE_TOKEN_FILE`. To re-authorize, delete that token file
(`rm ~/.config/jobjob/token.pickle`).

---

**See also:** [Profiles](profiles.md) · [Developer reference](developer.md)
