jobjob
======

Generate tailored resumes and cover letters at scale. Given a job description
(PDF, a URL, or pasted text), ``jobjob`` runs five sequential Claude calls — sharing
one cached context prefix — to parse the role, select credential highlights, tailor
the resume, draft a cover letter, and produce a skills gap analysis. It writes local
artifacts and (optionally) uploads to Google Drive.

New here? Start with **Getting Started**. The full configuration reference and the
profile model follow, then the API reference for the ``jobjob`` package.

.. toctree::
   :maxdepth: 2
   :caption: Guides

   getting-started
   configuration
   credentials-setup
   profiles
   usage
   architecture

.. toctree::
   :maxdepth: 2
   :caption: Reference

   api


Indices and tables
===================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
