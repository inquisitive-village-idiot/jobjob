jobjob documentation
=====================

**jobjob** generates tailored résumés and cover letters from a job posting. Give it a
job description (a PDF, a URL, or pasted text); it runs five sequential Claude calls —
sharing one cached context prefix — to parse the role, select the most relevant parts
of your background, tailor the résumé, draft a cover letter, and produce a skills-gap
analysis. Output is saved on your computer and, optionally, to Google Drive as editable
Docs.

It runs entirely on your machine as a small local website that you open in a browser.

.. admonition:: New here?
   :class: tip

   Start with :doc:`guide/index`. It takes you from nothing installed to your first
   finished application, with no command-line experience assumed.

This site has three parts:

- **User Guide** — install, configure, and use jobjob. Start here.
- **Library Reference** — the Python package internals, for contributors and scripting.
- **REST API Reference** — the local dashboard's HTTP API.

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   guide/index

.. toctree::
   :maxdepth: 2
   :caption: Library Reference

   library/index

.. toctree::
   :maxdepth: 2
   :caption: REST API Reference

   restapi/index

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
