Profiles
========

A **profile** is a self-contained directory holding everything jobjob tailors an
application from: your reusable credential blocks, skills, résumé archetypes, and the
reference documents that keep the AI honest. Switching profiles swaps the entire set at
once — useful for keeping one profile per role type.

Every profile has the same shape::

   <profile>/
     content/
       highlights.toml     reusable credential blocks the model selects from
       skills.toml         skills, with keywords for job-description matching
       templates.toml      résumé archetypes + editable sections
     reference/
       background.md       career narrative / context (sent on every generation)
       writing_style.md    voice and style guidance
       cover_letters/      *.txt / *.md / *.pdf — voice anchors
       stars/              STAR-format experience docs (honesty enforcement layer)
     config/
       .profile            applicant identity + résumé template id (no secrets)
     prompt/               optional: per-profile prompt overrides

The files
---------

**content/** — structured TOML that drives résumé customization. Edit these in the
dashboard's **Static Content** tab.

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - File
     - What it holds
   * - ``highlights.toml``
     - Credential blocks tagged with keywords. The model selects the most relevant ones
       per job description.
   * - ``skills.toml``
     - Skill entries with labels and keywords. Used in the skills-gap analysis.
   * - ``templates.toml``
     - Résumé archetypes (e.g. ``print_correspondent``) that map keywords to a Google
       Doc template id and editable sections.

**reference/** — free-text documents the model reads as context. Plain Markdown/text
(and PDFs for cover letters) — write them as you would for a person.

.. list-table::
   :header-rows: 1
   :widths: 28 72

   * - Path
     - What it holds
   * - ``background.*``
     - Career narrative, relocation intent, and context. Shared on every generation.
   * - ``writing_style.*``
     - Voice and writing rules the cover letter should follow.
   * - ``cover_letters/``
     - Example letters used as voice anchors (``*.txt`` / ``*.md`` / ``*.pdf``).
   * - ``stars/``
     - STAR-format experience documents. **The honesty layer:** the model draws claims
       from these rather than inventing them. A job requirement with no supporting STAR
       is flagged, not bridged.

.. important::

   jobjob never asserts a qualification it can't trace to your documents. The richer your
   ``stars/`` and ``highlights.toml``, the stronger and more truthful the output.

The three kinds of profile
--------------------------

All three use the *same* model; only their location differs.

- **example (read-only)** — the bundled demo persona, the fictional *Tila Mer* (a print
  science correspondent). It ships inside the package and can't be edited. Switch to it
  for reference, or **duplicate** it into a profile you own.
- **Local / owned** — under ``<jobjob folder>/profiles/<name>/``. New ones start
  **blank** from a valid-but-empty skeleton (no example content leaks in). Fill them in
  by hand, or by importing an existing résumé.
- **External** — a directory elsewhere on disk that you *register* (validated, never
  copied). Use this when you keep your content in its own repository — see
  :doc:`github-repo`.

The registry
------------

Profiles are listed in the app config (``config/.env``)::

   JOBJOB_PROFILE_<NAME>=/path/to/profile      # one line per profile
   JOBJOB_ACTIVE_PROFILE=<name>                # the active one

The ``example`` profile is always available without a registry entry. In the dashboard,
manage everything from **Settings → Profiles**: create, duplicate, register, switch, or
delete. Editing content while ``example`` is active is blocked — duplicate it first.

Creating your profile
---------------------

#. Open **Settings → Profiles**.
#. **Create blank** (then fill in **Static Content**), **Import a résumé** (jobjob
   extracts highlights, skills, objective, and background for you to review), or
   **Register** an existing folder.
#. Switch to it so it becomes active.
#. Fill in your details under setup / **Settings** (name, email, phone, LinkedIn) — these
   land in ``config/.profile``.

Next
----

→ :doc:`usage-applications`
