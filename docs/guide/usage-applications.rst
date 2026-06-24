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
#. Open the **Queue** tab, find the posting, and click **Apply**.
#. Watch progress. The finished application appears on the **Dashboard**.

.. warning::

   The cover letter starts with a ``⚠️ GAPS / FLAGS – DELETE BEFORE SENDING`` section
   listing anything the AI couldn't match to your documented background. **Review and
   delete it before sending.** jobjob flags gaps rather than inventing qualifications.

On the command line
-------------------

::

   jobjob apply <job_description.pdf> [options]

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

   jobjob apply path/to/job.pdf --skip-drive -o ./out

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

See also
--------

→ :doc:`configuration` · :doc:`profiles` · :doc:`usage-enrichment`
