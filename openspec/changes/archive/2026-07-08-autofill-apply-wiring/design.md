# Design: Autofill Apply Wiring

Settled in the 2026-07-06 explore session; specifics resolved here after
`application-identity` phase 1 landed (the posting URL now lives in
`source.json`). The assisted-autofill UX itself is unchanged from the CLI
(`jobjob apply <url>`): fill the contact basics the adapter can map, print a
fill report, and hand the open browser window to the human to finish custom
widgets / screening questions / resume upload / submit. This change only wires
that existing flow to the webapp.

## The core problem: browser lifecycle vs. the worker pool

`run_autofill` opens a headed persistent-context Chromium, fills, calls
`wait_for_human(report)`, then closes the context in a `finally`. So the browser
stays open **only while `wait_for_human` blocks**. That creates a bind for the
webapp:

- Running it in a jobs-framework worker **thread** with the default
  `_prompt_to_close` (which calls `input()`) both **wedges the thread** for the
  minutes a human takes and needs a **TTY** the backend doesn't have.
- Running it with a non-blocking `wait_for_human` returns immediately →
  `context.close()` fires → the browser closes before the human can finish.

## Decision: detached subprocess + a non-TTY "wait until window closed" mode

1. **Launch a detached subprocess**, not in-thread. The backend spawns
   `python -m jobjob apply <url>` (the existing autofill CLI) with
   `start_new_session=True` (its own process group) so it outlives the request
   and never consumes a jobs worker thread. The subprocess owns the browser and
   the human's session.

2. **Non-TTY wait mode in the runner.** Add a `wait_for_human` that blocks on the
   human **closing the browser window** instead of on stdin. The CLI selects it
   automatically when stdin is not a TTY (or via an explicit `--assisted-detached`
   flag the backend passes). Implementation: the runner waits on the persistent
   context's pages closing (e.g. poll `context.pages` / a close event) rather
   than `input()`. This keeps the window open for the human with no terminal.

3. **Record + surface via the jobs framework.** The launch is recorded in run
   history with `kind="apply"` (the reserved autofill kind from
   `full-build-rename`). The subprocess's stdout — which prints the rendered
   `FillReport` right after filling, *before* the window-close wait — is streamed
   into the run log. The job is marked **complete once the fill report is
   captured** (fill done, ~seconds), while the subprocess stays alive detached
   for the human. The worker thread returns promptly; nothing wedges.

   Rationale: the report is emitted early and deterministically; completing the
   job at that point gives the user their fill report in the Queue/log without
   tying job state to when the human happens to close the browser (which may be
   many minutes, or never in one sitting).

4. **URL gating via the source tier.** The Apply endpoint resolves the entity's
   `source.json` `web_uri`; it 400s when absent. The completed-application item
   gains a `posting_url` (the source `web_uri`, or None) so the frontend can
   enable the row action only when a URL is present, with a tooltip otherwise.
   URL/text ingests capture the URL automatically; PDF drops attach it later via
   the phase-1 source editor.

## API / surfaces

- `POST /jobs/apply` (the verb freed by `full-build-rename`; semantically =
  autofill): body identifies the application (folder_name and/or entity_id);
  backend reads the source `web_uri`, 400 if missing / no adapter host, else
  spawns the detached subprocess and records the run. Returns `{job_id}`.
- `tracking_service` completed item: add `posting_url`.
- Frontend `ApplicationsPage`: enable the reserved **Apply** row action when
  `posting_url` is set; launch via the endpoint; watch through the existing job
  progress modal; the run shows on the Queue page.

## Risks / bounds

- **Detached Chromium survives the request**; it dies only if the human closes
  it or the webapp process exits. Acceptable — it's a local single-user
  dashboard, and this mirrors what running the CLI already does.
- **Playwright not installed / no adapter for the host**: surfaced as a failed
  run (the subprocess exits non-zero with the existing `PlaywrightUnavailableError`
  / `NoAdapterError` messages captured to the log); the endpoint pre-checks the
  adapter host where cheap so the common "unsupported ATS" case fails fast.
- **Scope unchanged**: contact basics only; no resume upload, no submit, no
  multi-page automation.

## Out of scope

Multi-page automation, resume upload, submit, adapters beyond the current set.
