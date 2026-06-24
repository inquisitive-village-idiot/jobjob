#!/usr/bin/env python3
"""The structured payload an adapter fills from.

A small, config-free bundle of exactly what the adapters need: applicant identity
and work history. The runner builds this from ``Settings`` at the entry point so the
adapters stay decoupled from configuration and easy to test.
"""

import dataclasses as dcs

from jobjob.structure.applicant import Applicant
from jobjob.structure.experience import ExperienceSet


@dcs.dataclass(frozen=True)
class ApplicationData:
    """Everything an adapter needs to fill an application.

    Attributes:
        applicant: Contact identity (name/email/phone/linkedin).
        experience: Structured work history.
    """

    applicant: Applicant = dcs.field(default_factory=Applicant)
    experience: ExperienceSet = dcs.field(default_factory=ExperienceSet)


# __END__
