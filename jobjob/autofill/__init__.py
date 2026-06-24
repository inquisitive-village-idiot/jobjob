#!/usr/bin/env python3
"""Playwright-assisted auto-fill of online job applications.

Assisted, human-in-the-loop: an adapter fills the fields it can map confidently
from the active profile's structured data, records what it filled and what it
*deliberately left* for a human (account creation, CAPTCHA, ambiguous questions,
and the final submit), then the runner keeps the browser open so the person can
finish and submit. jobjob never auto-submits.
"""

# __END__
