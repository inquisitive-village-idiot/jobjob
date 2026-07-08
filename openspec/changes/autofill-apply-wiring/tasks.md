# Tasks: Autofill Apply Wiring

> Design in design.md. UX is the existing CLI autofill (fill contact basics,
> hand the open browser to the human). This wires it to the webapp as a detached
> background job, gated on the source `web_uri`.

## 1. Runner: non-TTY "wait until window closed" mode

- [ ] 1.1 `jobjob/autofill/runner.py`: add a wait mode that blocks on the human
  **closing the browser window** instead of `input()` (e.g. a
  `wait_for_window_close(context)` that waits while `context.pages` is non-empty
  / on the close event). Keep `_prompt_to_close` as the default; select the
  window-close wait when there is no TTY. Ensure `context.close()` still runs
  after (idempotent if already closed).
- [ ] 1.2 `jobjob/autofill/__main__.py`: select the window-close wait
  automatically when `sys.stdin` is not a TTY (or via an explicit
  `--assisted-detached` flag the backend passes). Print the fill report to
  stdout as today (before the wait) so it can be captured.

## 2. Backend launch endpoint (detached, recorded)

- [ ] 2.1 `webapp/backend/routers/jobs.py`: add `POST /jobs/apply` (autofill).
  Body identifies the application (folder_name and/or entity_id). Resolve the
  source `web_uri` via the source tier; 400 when absent. Where cheap, pre-check
  the adapter recognizes the host and 400 on unsupported ATS.
- [ ] 2.2 Launch `python -m jobjob apply <url>` as a **detached** subprocess
  (`start_new_session=True`), streaming its stdout into the run log; record the
  run with `kind="apply"` via the run-history/jobs plumbing. Mark the job
  complete once the fill report is captured (do NOT block on the human). Never
  wedge a worker thread.

## 3. Gating data on the application item

- [ ] 3.1 `webapp/backend/services/tracking_service.py`: add `posting_url` (the
  source `web_uri`, or None) to the completed-application item.

## 4. Frontend

- [ ] 4.1 `webapp/frontend/src/pages/ApplicationsPage.tsx`: enable the reserved
  **Apply** row action when `posting_url` is set; disabled with a tooltip
  otherwise (URL required, attachable via source editing). Launch via the new
  endpoint and watch through the existing job progress modal; the run appears on
  the Queue page. Update `types/index.ts` (`posting_url`).

## 5. Tests + docs

- [ ] 5.1 Backend: URL gating (400 without `web_uri`); launch wiring records a
  `kind="apply"` run and spawns detached (subprocess spawn + runner mocked — no
  real browser); fill report captured to the log; `posting_url` surfaced on the
  item. Runner: window-close wait selected without a TTY (mock the context/pages;
  no real Playwright).
- [ ] 5.2 Frontend: `tsc && vite build` + eslint green; Apply enable/disable by
  `posting_url`.
- [ ] 5.3 Docs: note the webapp Apply action (autofill from the Applications
  table, gated on a posting URL) in CLAUDE.md / the relevant docs page.
- [ ] 5.4 Run backend `pytest` as its own command; confirm green before push.
