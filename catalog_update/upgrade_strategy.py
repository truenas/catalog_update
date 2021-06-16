from pkg_resources import parse_version
from pkg_resources.extern.packaging.version import Version
from typing import Optional


def semantic_versioning(tags: list) -> Optional[str]:
    versions = [v for v in map(parse_version, tags) if isinstance(v, Version) and not v.is_prerelease]
    if not versions:
        return None

    versions.sort()
    return str(versions[-1])
