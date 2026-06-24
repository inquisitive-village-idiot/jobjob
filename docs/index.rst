jobjob
======

Generate tailored resumes and cover letters at scale. Given a job description
(PDF, a URL, or pasted text), ``jobjob`` runs five sequential Claude calls — sharing
one cached context prefix — to parse the role, select credential highlights, tailor
the resume, draft a cover letter, and produce a skills gap analysis. It writes local
artifacts and (optionally) uploads to Google Drive.

**New here? Start with Getting started** — it walks you from zero to your first
application. The rest is reference you reach for as needed.

.. toctree::
   :maxdepth: 1
   :caption: Start here

   quickstart

.. toctree::
   :maxdepth: 1
   :caption: Setup & usage

   setup
   usage-applications
   usage-enrichment

.. toctree::
   :maxdepth: 1
   :caption: Optional / advanced

   install-google-project
   install-free-option

.. toctree::
   :maxdepth: 1
   :caption: Reference

   profiles
   architecture
   developer

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api


Indices and tables
===================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
