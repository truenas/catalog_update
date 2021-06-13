import json
import os


from catalog_validation.validation import validate_catalog_item
from jsonschema import validate as json_schema_validate, ValidationError as JsonValidationError
from pkg_resources import parse_version
from typing import Optional

from .exceptions import ValidationException


class Item:
    def __init__(self, path: str):
        self.path = path

    @property
    def exists(self) -> bool:
        return os.path.exists(self.path)

    @property
    def upgrade_strategy_path(self) -> str:
        return os.path.join(self.path, 'upgrade_strategy')

    @property
    def upgrade_strategy_defined(self) -> bool:
        return os.path.isfile(self.upgrade_strategy_path) and os.access(self.upgrade_strategy_path, os.X_OK)

    @property
    def upgrade_info_path(self) -> str:
        return os.path.join(self.path, 'upgrade_info.json')

    @property
    def upgrade_info_defined(self) -> bool:
        return os.path.isfile(self.upgrade_info_path)

    def validate(self) -> None:
        validate_catalog_item(self.path, 'catalog_update')

    @property
    def upgrade_info_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'filename': {
                    'type': 'string',
                },
                'keys': {
                    'type': 'array',
                },
            },
            'required': ['filename', 'keys'],
        }

    def upgrade_info(self) -> Optional[dict]:
        if not self.upgrade_info_defined:
            return

        with open(self.upgrade_info_path, 'r') as f:
            info = json.loads(f.read())

        # We would like to validate that upgrade info is indeed valid and if it's
        # not we will raise an appropriate exception detailing the issue
        try:
            json_schema_validate(info, self.upgrade_info_schema)
        except JsonValidationError as e:
            raise ValidationException(f'Upgrade info failed validation: {e}')

        return info

    @property
    def latest_version(self) -> str:
        # We assume that we have at least one version available and that should be
        # validated by catalog_validation as well
        all_versions = [parse_version(d) for d in os.listdir(self.path) if os.path.isdir(os.path.join(self.path, d))]
        all_versions.sort()
        return str(all_versions[-1])

    def upgrade_summary(self) -> dict:
        summary = {
            'error': None,
            'latest_version': self.latest_version,
            'upgrade_available': False,
            'upgrade_details': {
                'filename': None,
                'keys': {},
            }
        }
        missing_files = []
        if not self.upgrade_info_defined:
            missing_files.append(self.upgrade_info_path)
        if not self.upgrade_strategy_defined:
            missing_files.append(self.upgrade_strategy_defined)

        if missing_files:
            summary['error'] = f'Missing {", ".join(missing_files)} required files'
            return summary

        upgrade_info = self.upgrade_info()
