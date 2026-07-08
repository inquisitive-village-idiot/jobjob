Applications
============

The core feature: give jobjob a job posting and it tailors a résumé summary and cover
letter from your active :doc:`profile <profiles>`, saving them locally and (optionally)
to Google Drive.

**Before you start:** finish :doc:`install`, :doc:`configuration`, and
:doc:`profiles` (add some background content). Configuration keys for this feature live
under *Applications* in the :doc:`configuration reference <configuration>`.

In the app
----------

#. **Add a job posting** — click **Add JD**, then *paste the text*, *fetch a URL*, or
   *upload a PDF*. (You can also drop a PDF into ``<jobjob folder>/data/jobs/``.)
#. On the **Applications** page, find the posting (state *Queued*) and choose
   **Build** from its actions.
#. Watch progress. While a document-generation run is in flight the row shows a
   live **Building…** indicator — even if the build was launched from a batch,
   a schedule, or another browser tab — and clears automatically (the page
   refreshes the run listing every few seconds). The finished application
   flips to *Built* in the same table; past runs (and any errors) stay on the
   **Queue** page.

.. warning::

   The cover letter starts with a ``⚠️ GAPS / FLAGS – DELETE BEFORE SENDING`` section
   listing anything the AI couldn't match to your documented background. **Review and
   delete it before sending.** jobjob flags gaps rather than inventing qualifications.

On the command line
-------------------

::

   jobjob build <job_description.pdf> [options]

.. note::

   ``jobjob apply`` means something different than it used to — it now runs
   assisted browser auto-fill (formerly ``jobjob autofill``), not document
   generation. Document generation is ``jobjob build``.

The positional argument is a job-description PDF, or a directory of mixed inputs (only
job descriptions are processed; other files are skipped).

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Flag
     - Description
   * - ``-o`` / ``--output <dir>``
     - Output directory (default: ``./out/<date> - <Company> - <Role>/``).
   * - ``--skip-drive``
     - Local artifacts only; no Google Drive/Docs.
   * - ``--template <name>``
     - Force a résumé archetype (otherwise the model classifies the JD).
   * - ``--no-cache``
     - Disable the response cache for this run.
   * - ``--clear-cache``
     - Purge the response cache before running.
   * - ``--reprocess``
     - Re-run a previous application in place. Point at the JD copy inside its output
       directory; that directory (and the original Drive folder) is regenerated.

Example — local only, custom output folder::

   jobjob build path/to/job.pdf --skip-drive -o ./out

Re-checking a resume
--------------------

::

   jobjob ats <output_dir>

Re-assesses a processed application's résumé against its job description — keyword
coverage plus parseability checks — and prints a plain-text report. Point it at the
application's output directory (the one containing ``summary.json``).

Use it while iterating: edit the résumé Google Doc, run ``jobjob ats``, repeat. The
assessment is rebuilt from the saved artifacts plus one Google Docs read of the current
résumé — **no AI calls**, so the loop is free. Applications generated with
``--skip-drive`` have no résumé Doc to read and report a skipped assessment.

What you need
-------------

- **A job posting** — a PDF, a URL, or pasted text.
- **An active profile with content** — see :doc:`profiles`. Output quality tracks how
  well your ``highlights.toml`` and ``stars/`` cover the role.
- *(Optional)* **Google connected** — for editable Docs output; otherwise everything is
  local. See :doc:`google-project`.

Where output lands
------------------

**Locally**, under ``<jobjob folder>/data/completed/`` (or ``--output``)::

   YYYY-MM-DD - Company - Role/
     JD_Company_Role.pdf   Resume.pdf   CoverLetter.pdf / .docx
     skills_analysis.json  README.docx  summary.json

**On Google Drive** (if connected): a folder ``YYYY-MM-DD - Company - Role`` under your
``APPLICATIONS_OUTPUT_DRIVE_ID``, holding the README, JD copy, Résumé, and CoverLetter
as editable Google Docs.

Identity: entity, source, and executions
-----------------------------------------

Each application folder now carries a stable ``entity_id`` (a uuid minted once,
in ``metadata.json``, and reused across re-builds/renames) plus a ``source.json``
recording the posting itself — company, role, a one-time summary, and any file
or web URI. The summary/company/role are written **once**, at first build; a
re-build reads them back rather than overwriting them, so a correction survives.
Correct a parse mistake (company, role, posting URL, or an external requisition
id) from the application's row actions (**Edit source**) — this never touches
the résumé, cover letter, or any other artifact. A folder built before this
change has neither field; it behaves exactly as it always has (joined by folder
name) until its next build, when the id is added automatically.

Applying from the dashboard
----------------------------

The Applications table's row actions include **Apply** — assisted browser
auto-fill (``jobjob apply``, see above) launched for that application, gated on
a posting URL: it's disabled with a tooltip until one is present (a URL/text
ingest captures it automatically; a PDF drop needs one attached via **Edit
source** first). Launching it starts a detached background process — the run
shows up in the Queue like any other job, with the fill report in its log —
and opens a real browser window on the machine running the dashboard for you
to finish account creation, custom widgets, screening questions, and the
submit.

See also
--------

→ :doc:`configuration` · :doc:`profiles` · :doc:`usage-enrichment`
