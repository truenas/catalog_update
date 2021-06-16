from datetime import datetime
from pkg_resources import parse_version
from pkg_resources.extern.packaging.version import Version
from typing import Optional


def semantic_versioning(tags: list) -> Optional[str]:
    versions = [v for v in map(parse_version, tags) if isinstance(v, Version) and not v.is_prerelease]
    if not versions:
        return

    versions.sort()
    return str(versions[-1])


def datetime_versioning(tags: list, date_format: str) -> Optional[str]:
    versions = [datetime.strptime(t, date_format) for t in tags]
    if not versions:
        return

    versions.sort()
    return versions[-1].strftime(date_format)
