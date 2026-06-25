REST API Reference
==================

The local dashboard is a **FastAPI** backend. Its HTTP API is what the browser UI calls;
you can also script against it. The server binds to ``127.0.0.1`` only — it is never
exposed to the network.

Interactive docs
----------------

The most accurate, always-current reference is the **OpenAPI** page the server generates
from the code. With jobjob running, open:

   http://127.0.0.1:8000/api/docs

It lists every endpoint, its parameters, and its response schema, and lets you try calls
live. The OpenAPI schema itself is at ``http://127.0.0.1:8000/openapi.json``.

Conventions
-----------

- **Base URL** — ``http://127.0.0.1:8000``. All endpoints below are under ``/api``.
- **CSRF** — every state-changing request (``POST``/``PUT``/``PATCH``/``DELETE``) must
  send an ``X-CSRF-Token`` header matching the ``csrf_token`` cookie (double-submit
  pattern).
- **Secrets** — secret values (e.g. ``ANTHROPIC_API_KEY``) are **never** returned; the
  config endpoints report them as set / not set only.
- **Cost guard** — per-run and daily spend budgets are enforced before any job launches.

Endpoint groups
---------------

Each group is mounted under the prefix shown. See the interactive docs for full request
and response shapes.

.. list-table::
   :header-rows: 1
   :widths: 22 24 54

   * - Group
     - Prefix
     - Purpose
   * - setup
     - ``/api/setup``
     - First-run wizard: setup ``status``, save the Anthropic key, upload Google
       ``credentials``, run ``google-auth``, and ``dismiss`` the wizard.
   * - config
     - ``/api/config``
     - Read (``GET``) and update (``PUT``) the app config (``config/.env``); secrets are
       masked.
   * - profiles
     - ``/api/profiles``
     - List profiles and resources; set the ``active`` profile; create, ``duplicate``,
       ``register``, and delete profiles.
   * - static
     - ``/api/static``
     - Read/write the active profile's ``content/`` TOML and ``reference/`` documents
       (the **Static Content** tab).
   * - prompts
     - ``/api/prompts``
     - List, update, and reset the active profile's prompt templates.
   * - resume-import
     - ``/api/resume-import``
     - ``extract`` highlights/skills/objective/background from an uploaded résumé, then
       ``save`` them into a profile.
   * - jobs
     - ``/api/jobs``
     - Launch work: ``apply`` (and ``apply/from-url``, ``apply/from-text``,
       ``apply/rerun``), ``enrich``, batch ``apply-all`` / ``enrich-all``, ``schedule``
       runs, and poll a job's ``progress`` / ``status``.
   * - tracking
     - ``/api/tracking``
     - The ``queue`` and ``completed`` lists; update an application's ``status`` and read
       or append its ``notes``.
   * - update
     - ``/api/update``
     - Check for and apply jobjob version updates (**Settings → Update**).

.. note::

   This table is an orientation map, not a contract. Endpoint paths and payloads can
   change between releases — treat the live ``/api/docs`` page as the source of truth.
