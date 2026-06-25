User Guide
==========

jobjob runs on your own machine as a small local website. It does two things:

#. **Application Builder** — give it a job posting (PDF, URL, or pasted text). It reads
   the posting, picks the most relevant parts of your background, and writes a tailored
   cover letter and résumé summary. Output is saved on your computer and, optionally, to
   Google Drive as editable Docs.
#. **Contact Enrichment** — give it a PDF or screenshot of a LinkedIn profile. It parses
   out the details and appends them to a Google spreadsheet.

Everything below works on **Windows, macOS, and Linux**. Plan on 30–60 minutes the first
time — most of that is the one-time account setup. After that, each application takes a
couple of minutes.

Follow the pages in order.

.. rubric:: Steps

#. :doc:`prerequisites` — install Python (or ``uv``, which brings its own).
#. :doc:`credentials` — get an Anthropic API key; optionally set up Google.
#. :doc:`install` — install the ``jobjob`` app.
#. :doc:`configuration` — launch jobjob and finish setup.
#. :doc:`profiles` — set up your content profile.
#. :doc:`usage-applications` — generate your first application.

.. rubric:: Reference and optional topics

- :doc:`usage-enrichment` — import LinkedIn contacts into a Google Sheet.
- :doc:`google-project` — create the Google project needed for Drive/Docs output.
- :doc:`github-repo` — keep your profile content in a Git/GitHub repository.
- :doc:`free-option` — run on a free Google AI backend instead of a paid key.

.. toctree::
   :hidden:

   prerequisites
   credentials
   install
   configuration
   profiles
   usage-applications
   usage-enrichment
   google-project
   github-repo
   free-option
