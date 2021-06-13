import distutils.dir_util
import json
import itertools
import os
import subprocess
import yaml

from catalog_validation.validation import validate_catalog_item
from collections import defaultdict
from jsonschema import validate as json_schema_validate, ValidationError as JsonValidationError
from pkg_resources import parse_version
from typing import Optional

from .docker_utils import get_image_tags
from .exceptions import ValidationException
from .utils import get, run


class Item:
    def __init__(self, path: str):
        self.path = path

    @property
    def name(self) -> str:
        return self.path.split('/')[-1]

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

    @property
    def image_schema(self) -> dict:
        return {
            'type': 'object',
            'properties': {
                'repository': {
                    'type': 'string',
                },
                'tag': {
                    'type': 'string',
                },
            },
            'required': ['repository', 'tag'],
        }

    def upgrade_summary(self) -> dict:
        keys_details = defaultdict(lambda: {
            'value': None,
            'available_tags': [],
            'error': 'Unable to locate key',
            'latest_tag': None,
            'current_tag': None,
        })
        summary = {
            'error': None,
            'latest_version': self.latest_version,
            'upgrade_available': False,
            'upgraded': False,
            'upgrade_details': {
                'filename': None,
                'keys': keys_details,
            }
        }
        missing_files = []
        if not self.upgrade_info_defined:
            missing_files.append(self.upgrade_info_path)
        if not self.upgrade_strategy_defined:
            missing_files.append(self.upgrade_strategy_path)

        if missing_files:
            summary['error'] = f'Missing {", ".join(missing_files)} required files'
            return summary

        try:
            upgrade_info = self.upgrade_info()
        except ValidationException as e:
            summary['error'] = str(e)
            return summary

        values_file = os.path.join(self.path, summary['latest_version'], upgrade_info['filename'])
        summary['upgrade_details']['filename'] = upgrade_info['filename']
        if not os.path.exists(values_file):
            summary['error'] = f'{values_file!r} count not be found'
            return summary

        if not upgrade_info['keys']:
            summary['error'] = f'No keys listed in {self.upgrade_info_path!r} for upgrade check'
            return summary

        with open(values_file, 'r') as f:
            try:
                values = yaml.safe_load(f.read())
            except yaml.YAMLError:
                summary['error'] = f'{values_file!r} is an invalid yaml file'
                return summary

        for key in upgrade_info['keys']:
            val = get(values, key)
            keys_details[key]['value'] = val
            if not val:
                continue
            try:
                json_schema_validate(val, self.image_schema)
            except JsonValidationError as e:
                keys_details[key]['error'] = f'Image format is invalid: {e}'
                continue
            else:
                keys_details[key]['current_tag'] = val['tag']

            try:
                keys_details[key]['available_tags'] = get_image_tags(val['repository'])['Tags']
            except subprocess.CalledProcessError as e:
                keys_details[key]['error'] = f'Failed to retrieve available image tags: {e}'
            else:
                keys_details[key]['error'] = None

        # We have information on each available image now, let's pass it to upgrade strategy
        cp = run(
            [self.upgrade_strategy_path, json.dumps({k: v['available_tags'] for k, v in keys_details.items()})],
            check=False
        )
        if cp.returncode:
            summary['error'] = f'Failed to retrieve latest available image tag(s): {cp.stderr}'
            return summary

        try:
            tags_info = json.loads(cp.stdout)
        except json.JSONDecodeError:
            summary['error'] = f'Expected json compliant output from {self.upgrade_strategy_path}'
            return summary

        if not isinstance(tags_info, dict) or any(
            not isinstance(v, str) for v in itertools.chain(tags_info.keys(), tags_info.values())
        ):
            summary['error'] = 'Unexpected output format specified by upgrade strategy'
            return summary

        for tag in filter(lambda t: t in keys_details, tags_info):
            keys_details[tag]['latest_tag'] = tags_info[tag]
            if tags_info[tag] != keys_details[tag]['current_tag']:
                summary['upgrade_available'] = True

        if not summary['upgrade_available']:
            summary['error'] = 'No update available'

        return summary

    @property
    def bump_version(self) -> str:
        v = parse_version(self.latest_version)
        return str(parse_version(f'{v.major}.{v.minor}.{v.micro + 1}'))

    @property
    def bump_version_path(self) -> str:
        return os.path.join(self.path, self.bump_version)

    @property
    def latest_version_path(self) -> str:
        return os.path.join(self.path, self.latest_version)

    def upgrade(self) -> dict:
        summary = self.upgrade_summary()
        if summary['error']:
            return summary

        new_path = self.bump_version_path
        new_version = new_path.rsplit('/', 1)[-1]
        distutils.dir_util._path_created = {}
        distutils.dir_util.copy_tree(self.latest_version_path, new_path, preserve_symlinks=True)

        with open(os.path.join(new_path, summary['upgrade_details']['filename']), 'r') as f:
            values = yaml.safe_load(f.read())

        for key, value in summary['upgrade_details']['keys'].items():
            if value['error'] or value['latest_tag'] == value['current_tag']:
                continue
            image = get(values, key)
            image['tag'] = value['latest_tag']

        with open(os.path.join(new_path, summary['upgrade_details']['filename']), 'w') as f:
            f.write(yaml.safe_dump(values))

        chart_file_path = os.path.join(new_path, 'Chart.yaml')
        with open(chart_file_path, 'r') as f:
            chart = yaml.safe_load(f.read())

        # TODO: Allow changing app version as well
        chart['version'] = new_version

        with open(chart_file_path, 'w') as f:
            f.write(yaml.safe_dump(chart))

        summary.update({
            'upgraded': True,
            'new_version': new_version,
            'new_version_path': new_path,
        })
        return summary
