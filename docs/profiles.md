# Profiles

A **profile** is a self-contained directory holding everything `jobjob` tailors an
application from. Every profile has the same shape:

```
<profile>/
  content/
    highlights.toml     # reusable credential blocks the model selects from
    skills.toml         # skills, with keywords for JD matching
    templates.toml      # resume archetypes + editable sections
  reference/
    background.md       # career narrative / context (shared on every generation)
    writing_style.md    # voice and style guidance
    cover_letters/      # *.txt/*.md/*.pdf — voice anchors
    stars/              # STAR-format experience docs (honesty enforcement layer)
  config/
    .profile            # applicant identity + resume template id (no secrets)
  prompt/               # optional: per-profile prompt overrides
```

Switching profiles swaps the entire content set at once — useful for keeping, say, one
profile per role type.

## The three kinds of profile

All three are *the same model*; only their location differs.

- **`example` (read-only)** — the bundled demo persona (the fictional *Tila Mer*, a
  print science correspondent). It ships inside the package and cannot be edited; it's
  there to switch to for reference or to **duplicate** into a profile you own.
- **Local / owned profiles** — live under `<JOBJOB_HOME>/profiles/<name>/`. New ones
  start **blank** from a skeleton (valid-but-empty content, placeholder reference docs,
  a blank `config/.profile`) — no example content leaks in. Fill them in by hand or by
  importing an existing résumé.
- **External profiles** — an existing directory elsewhere on disk that you *register*
  (it is validated, never copied). Use this when you already maintain your content in
  its own repo.

## The registry

Profiles are registered in the app config (`config/.env`):

```sh
JOBJOB_PROFILE_<NAME>=/path/to/profile      # one line per profile
JOBJOB_ACTIVE_PROFILE=<name>                # the active one
```

The `example` profile is always available without a registry entry. In the dashboard,
manage profiles from **Settings → Profiles**: create, duplicate, register, switch, or
delete. Editing content while the `example` profile is active is blocked — duplicate it
first.

## Migration from older layouts

Installs that predate the unified model kept a single `<JOBJOB_HOME>/profile/` directory.
On launch, `jobjob-app` moves it to `<JOBJOB_HOME>/profiles/local/` and rewrites the
registry path automatically — nothing is lost, and the step is idempotent.
