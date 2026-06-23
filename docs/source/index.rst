jobjob
======

Generate tailored resumes and cover letters at scale. Given a job description
(PDF, a URL, or pasted text), ``jobjob`` runs five sequential Claude calls — sharing
one cached context prefix — to parse the role, select credential highlights, tailor
the resume, draft a cover letter, and produce a skills gap analysis. It writes local
artifacts and (optionally) uploads to Google Drive.

New here? Start with **Getting Started**, then work through Installation, Setup, and
Usage. Reference material and the ``jobjob`` package API follow.

.. toctree::
   :maxdepth: 1
   :caption: Start here

   getting-started

.. toctree::
   :maxdepth: 1
   :caption: Installation

   install-accounts
   install-google-project
   install-software
   install-free-option

.. toctree::
   :maxdepth: 1
   :caption: Setup

   setup-wizard
   setup-local-config

.. toctree::
   :maxdepth: 1
   :caption: Usage

   usage-applications
   usage-enrichment

.. toctree::
   :maxdepth: 1
   :caption: Reference

   profiles
   architecture
   configuration

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   api


Indices and tables
===================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
