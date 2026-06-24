Enrichment
==========

Enrichment reads a **LinkedIn profile screenshot** (PDF or image) and appends the parsed
contact to a Google **Sheet** — handy for tracking recruiters and hiring managers
alongside your applications.

**Before you start:** finish :doc:`install` and :doc:`configuration`, including Google
access with the **Sheets API** enabled (see :doc:`google-project`). The relevant config
keys are ``ENRICHMENT_OUTPUT_SHEET_ID`` (the target spreadsheet) and, optionally,
``ENRICHMENT_INPUT_DIR`` — see the :doc:`configuration reference <configuration>`.

In the app
----------

#. Add a LinkedIn profile screenshot (PDF/image) — drop it into
   ``<jobjob folder>/data/profiles/``.
#. Open the **Queue** tab, find it, and click **Enrich**.
#. The parsed contact is appended to your contacts Sheet; the item moves to completed.

On the command line
-------------------

::

   jobjob enrich <profile> [options]

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Flag
     - Description
   * - ``--sheet-id <id>``
     - Spreadsheet id (overrides ``ENRICHMENT_OUTPUT_SHEET_ID``).
   * - ``--sheet-name <name>``
     - Worksheet tab name (default: ``Contacts``).
   * - ``--dry-run``
     - Parse only; don't write to the Sheet.
   * - ``--no-cache``
     - Disable the response cache for this run.

.. tip::

   Run with ``--dry-run`` first to confirm the profile parses, then run for real and
   check the new row in your Sheet.

Finding your Sheet id
---------------------

Open the Sheet in your browser. The id is the long string in the URL between ``/d/`` and
``/edit``. Put it in ``ENRICHMENT_OUTPUT_SHEET_ID`` (see :doc:`configuration`) or pass
``--sheet-id``.

See also
--------

→ :doc:`configuration` · :doc:`usage-applications`
