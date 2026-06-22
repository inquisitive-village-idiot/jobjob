#!/usr/bin/env python3
"""LinkedIn profile data extracted from a profile screenshot."""

import dataclasses as dcs


@dcs.dataclass
class LinkedInProfile:
    """Structured data extracted from a LinkedIn profile.

    NOTE: field docs drive the extraction prompt (see
        static/prompt/linkedin_profile.txt), the same way JobDescription does.
    """

    name: str = dcs.field(metadata={"doc": "The person's full name"})
    role: str = dcs.field(metadata={"doc": "Their current job title / role"})
    company: str = dcs.field(metadata={"doc": "Their current company or organization"})
    location: str = dcs.field(
        metadata={"doc": "Their location (city, region, country)"}
    )
    headline: str = dcs.field(metadata={"doc": "Their LinkedIn headline / tagline"})
    linkedin_url: str = dcs.field(
        metadata={
            "doc": "Their LinkedIn profile URL (linkedin.com/in/...) if visible, "
            "else empty"
        }
    )


# __END__
