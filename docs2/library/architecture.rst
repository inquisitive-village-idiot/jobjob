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
     - The application workflow; ``generate/`` holds the five AI-call steps and
       ``output/`` the PDF/DOCX builders.
   * - ``jobjob/enrich/``
     - LinkedIn-profile ingestion into the contacts Sheet.
   * - ``jobjob/gapi/``
     - Google Drive/Docs/Sheets I/O.
   * - ``jobjob/__main__.py``
     - CLI dispatcher (``apply``, ``enrich``, ``auth``).
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
- **Local file cache** — SHA256-keyed under ``CACHE_DIR``; skips identical prompts on
  re-runs. Toggle with ``CLAUDE_CACHE_ENABLED``.

Webapp
------

A local dashboard (FastAPI backend + React frontend) manages the queue, launches jobs,
edits profile content, and reviews results. It binds to ``127.0.0.1`` only and protects
state-changing endpoints with a CSRF double-submit cookie. Its HTTP surface is documented
in the :doc:`/restapi/index`.

Running from source
-------------------

Prerequisites: Python ≥ 3.12 and `uv <https://docs.astral.sh/uv/>`_ (or plain ``pip``)::

   uv sync                          # create the venv and install dependencies
   uv run --group test pytest       # run the test suite
   uv run ruff check .              # lint
   uv run --group docs sphinx-build -b html docs2 docs2/build   # build these docs

Run the webapp dev servers (two terminals)::

   # backend
   cd webapp/backend && uvicorn main:app --host 127.0.0.1 --port 8000 --reload
   # frontend
   cd webapp/frontend && npm install && npm run dev

See ``webapp/README.md`` for details.
