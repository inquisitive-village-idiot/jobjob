Architecture
============

``jobjob`` is a Python package providing a command-line interface and a local webapp,
plus a bundled dashboard frontend.

Package layout
--------------

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Module
     - Role
   * - ``jobjob/config.py``
     - Central ``Settings``, loaded once from ``config/.env`` plus the active profile's
       ``config/.profile``. Config is read at the entry point and injected into the
       workflow; feature modules take plain parameters and never read the environment
       themselves.
   * - ``jobjob/loader/``
     - Auth, prompt/content/reference loaders, and static-file location.
       ``profiles.py`` resolves the registry and active profile; ``location.py`` resolves
       ``content``/``reference``/``prompt`` (falling back to the bundled example);
       ``loadcontent.py`` loads the TOML; ``skeleton.py`` writes a blank-but-valid
       profile.
   * - ``jobjob/ailib/``
     - AI orchestration: ``query`` (retry + cache), ``client/`` (thin provider adapters,
       e.g. ``anthropic.py``), ``session.py`` (``AIClient``: cached context + token
       usage), and the cache manager.
   * - ``jobjob/structure/``
     - Typed domain models (job description, highlight, skill, template, …).
   * - ``jobjob/apply/``
     - The application-generation workflow (CLI verb ``jobjob build``; the module
       keeps its historical name); ``generate/`` holds the five AI-call steps and
       ``output/`` the PDF/DOCX builders.
   * - ``jobjob/autofill/``
     - Assisted browser auto-fill of a job application (CLI verb ``jobjob apply``).
   * - ``jobjob/enrich/``
     - LinkedIn-profile ingestion into the contacts Sheet.
   * - ``jobjob/gapi/``
     - Google Drive/Docs/Sheets I/O.
   * - ``jobjob/__main__.py``
     - CLI dispatcher (``build``, ``apply``, ``enrich``, ``auth``, ``ats``, ``skills``).
   * - ``jobjob/launcher.py``
     - The ``jobjob-app`` entry: scaffolds the working dir and serves the webapp.

Adding another AI provider is a single new adapter under ``jobjob/ailib/client/``.

How a run works
---------------

Five sequential Claude calls per application share one cached context prefix (résumé,
STAR examples, cover-letter examples, background):

#. **JD parse** — extract role level, domain, required skills, location, requirements.
#. **Highlight selection** — pick the most relevant credential blocks for the role.
#. **Résumé update** — swap the objective and adjust emphasis on the Google Doc template
   via section-aware edits.
#. **Cover-letter generation** — assemble from the selected blocks, mirror JD language.
#. **Skills analysis** — gap check; flag anything not met or not honestly claimable.

Caching
-------

- **Anthropic prompt cache** — stable context is sent as a cached system prefix and
  reused across all five calls (ephemeral, ~5 min, extended by hits). Keep stable content
  at the top; variable content (JD, company) at the end.
- **Local file cache** — SHA256-keyed under ``CACHE_DIR``, scoped by model so the
  same prompt under a different model never collides; skips identical prompts on
  re-runs. Toggle with ``CLAUDE_CACHE_ENABLED``.

Webapp
------

A local dashboard (FastAPI backend + React frontend) manages the queue, launches jobs,
edits profile content, and reviews results. It binds to ``127.0.0.1`` only and protects
state-changing endpoints with a CSRF double-submit cookie. Its HTTP surface is documented
in the :doc:`/restapi/index`.

Every launched job (build, autofill, enrich, batch, schedule) is a **run**: an
in-memory job table drives live progress, but each run is also persisted as a
JSON record plus a log file under ``<applications input dir>/runs/`` (see
``webapp/backend/services/run_history.py``), so history — including failures —
survives a backend restart instead of living only in memory. Listing merges
the persisted records with the live job table; a persisted run still marked
``running`` with no live counterpart is reported ``failed`` ("interrupted").
Records are bounded (oldest pruned beyond a retention cap) and, once a
finished run's application is known, carry that application's ``entity_id``.

Application identity: three tiers
----------------------------------

Each processed application (or contact) folder is modeled as three tiers, held
together by one on-disk folder:

- **Entity** — ``metadata.json``: a stable ``entity_id`` (uuid4, minted once and
  reused across every re-build/rename), status, and the notes changelog.
- **Source** — ``source.json``: the posting itself (company, role, description,
  and a file/web/external reference), written once at first build; a re-build
  reads it back rather than overwriting it, so a user correction (via
  **Edit source**) survives. **Re-parse** is the sanctioned exception —
  it deliberately overwrites company/role/description.
- **Execution** — the artifacts of one build: ``summary.json`` plus the
  generated documents. The current execution lives at the folder root; prior
  executions kept on a re-build move into ``archive/<timestamp>/`` (a
  self-contained snapshot), manageable per-execution (note, lock/unlock
  against purge, promote back to root, purge unlocked).

A folder with neither ``entity_id`` nor ``source.json`` is legacy: it joins by
folder name exactly as before, and gains an id lazily on its next natural
write — no backfill.

Duplicate applications (same normalized company + role) are flagged
advisory-only; resolving one either **merges** the loser's current and
archived executions into the survivor's ``archive/`` and unions its notes, or
**deletes** the loser outright. Both actions are always explicit, never
automatic (``webapp/backend/services/dedup_service.py``).

Running from source
-------------------

Prerequisites: Python ≥ 3.12 and `uv <https://docs.astral.sh/uv/>`_ (or plain ``pip``)::

   uv sync                          # create the venv and install dependencies
   uv run --group test pytest       # run the test suite
   uv run ruff check .              # lint
   uv run --group docs sphinx-build -b html docs docs/build   # build these docs

Run the webapp dev servers (two terminals)::

   # backend
   cd webapp/backend && uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   # frontend
   cd webapp/frontend && npm install && npm run dev

See ``webapp/README.md`` for details.
