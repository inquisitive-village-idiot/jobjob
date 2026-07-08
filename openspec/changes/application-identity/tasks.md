# Tasks: Application Identity — Phase 1 (identity core)

> Phase 1 only. Phases 2 (dedup) and 3 (versioned executions) are a later slot;
> do NOT implement them here. The openspec change is archived after phase 3, so
> this PR does not archive it.
>
> Invariants (from design.md — hold these everywhere):
> - **Mint-once / reuse-on-rebuild**: `entity_id` is a uuid4 minted at first
>   processing and reused on every re-build of the same folder — never regenerated.
> - **Parse-once**: source parse fields are written once; re-builds read, never
>   overwrite them (explicit re-parse is phase 2, out of scope).
> - **Absence = legacy**: no `entity_id`/`source.json` ⇒ today's behavior exactly
>   (join by name); mint lazily on next natural write; no backfill/mirror rewrite.
> - **Tolerant reads**: `source.json` reads like `metadata.json` — missing/corrupt
>   degrades to legacy, never crashes a listing.
> - Do NOT bump `metadata.json` `_SCHEMA_VERSION` (2); `entity_id` is an additive,
>   round-tripped key.

## 1. Source tier: reader/writer

- [ ] 1.1 New `webapp/backend/services/application_source.py` (sibling of
  `application_metadata.py`): `SOURCE_FILENAME = "source.json"`;
  `read_source(folder) -> dict` (tolerant, `{}` when absent, `_migrate`-style
  passthrough); `write_source(folder, data)` (atomic temp+`os.replace`, mirror
  the metadata writer); `ensure_source(folder, *, entity_id, company, role,
  description, file_uri=None, web_uri=None, external_ref=None)` that writes
  `source.json` ONLY when absent (parse-once), returning the effective dict;
  `edit_source(folder, **fields)` updating only `company/role/web_uri/
  external_ref`. Stamp a `schema_version`.

## 2. Entity id + source at build time

- [ ] 2.1 `application_metadata.py`: add `ensure_entity_id(folder) -> str` —
  read existing `metadata.json`, reuse its `entity_id` if present, else mint
  `uuid4` and write it (preserving status/notes/schema_version). Add an
  `entity_id` accessor. (metadata.json is the entity-tier home; this CREATES it
  at build when absent.)
- [ ] 2.2 `jobjob/apply/workflow.py` `run_application_workflow`: near
  `_write_summary(output_dir, results)`, mint/reuse the entity id for
  `output_dir` and `ensure_source(...)` from the parsed `job` (company, role,
  description; `file_uri` from the JD path; `web_uri` when the input was a URL
  snapshot). Put `results["entity_id"] = <id>` so callers can record it. Guard
  so a temp-dir/offline run still works (best-effort; never fail the build on a
  metadata write error — log and continue).

## 3. Run records carry entity_id

- [ ] 3.1 `webapp/backend/services/run_history.py`: `finish_run(...)` accepts an
  optional `entity_id` and merges it into the stored record (start_run may also
  accept it as None). Omit the key when None (legacy).
- [ ] 3.2 `webapp/backend/routers/jobs.py`: after the build run returns, pass
  `results.get("entity_id")` into `finish_run` for build runs.

## 4. Id-preferring joins (name fallback)

- [ ] 4.1 `webapp/backend/services/tracking_service.py`: surface `entity_id` on
  each application item (read from `metadata.json`); where runs are matched to
  application folders, prefer `entity_id` equality, fall back to `folder_name`
  as today.
- [ ] 4.2 `webapp/backend/routers/jobs.py` `_find_rerun_jd`: when the target
  carries an `entity_id`, resolve by id first, then fall back to the folder-name
  lookup. Legacy (no id) path unchanged.

## 5. Source-field editing API

- [ ] 5.1 `webapp/backend/routers/tracking.py`: add `PATCH
  /applications/{folder_name}/source` accepting `{company?, role?, web_uri?,
  external_ref?}`, calling `application_source.edit_source`; return the updated
  source. 404 when the folder is unknown; reject unknown/forbidden fields
  (`description`, `entity_id`). Add a `GET /applications/{folder_name}/source`.
- [ ] 5.2 Expose `entity_id` + source fields on the completed-application item
  so the frontend can render/edit them.

## 6. Contacts identity

- [ ] 6.1 `jobjob/enrich/workflow.py` `write_profile_sidecar` (and the enrich
  flow): mint/reuse an `entity_id` and record it in the profile `.json` sidecar.
- [ ] 6.2 `jobjob/gapi/sheets.py` `append_profile`: write the `entity_id` under
  an `ID` header column (extend the field→header map; keep the full-width /
  header-aligned append behavior intact). Tolerate a sheet without the column.

## 7. Frontend (minimal)

- [ ] 7.1 `webapp/frontend/src`: show the short `entity_id` prefix as a small
  subtitle on the application row/detail (never the primary name); add a minimal
  source-edit affordance (company / role / URL / external ref) wired to `PATCH
  /applications/{folder_name}/source`. Update `types/index.ts` for the new
  fields. Keep it minimal and functional.

## 8. Tests + docs

- [ ] 8.1 Backend tests: entity id mint-once + reuse-on-rebuild; `source.json`
  parse-once (re-build no overwrite) + tolerant read; `edit_source` only touches
  allowed fields; run record carries entity_id (and omits when legacy);
  id-preferring join resolves across a rename and falls back by name; contacts
  sidecar + sheet ID column. Follow the repo's unittest/subTest + result/
  expected/found style; mock Sheets.
- [ ] 8.2 Frontend: `tsc && vite build` + eslint green; update tests referencing
  changed types/items.
- [ ] 8.3 Docs: note the entity/source model (entity_id in metadata.json,
  source.json, editable fields) in CLAUDE.md and the relevant docs/ page.
- [ ] 8.4 Run backend `pytest` as its own command; confirm green before push.
