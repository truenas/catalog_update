#!/usr/bin/env python
import argparse
import functools
import os
import textwrap

from catalog_update.exceptions import TrainNotFound
from catalog_update.git_utils import (
    create_pull_request, checkout_branch, commit_changes, generate_branch_name, push_changes, update_branch
)
from catalog_update.update import update_items_in_train
from dotenv import dotenv_values
from jsonschema import validate as json_schema_validate, ValidationError as JsonValidationError


def update_items(train_path: str, remove_old_versions: bool) -> dict:

    try:
        summary = update_items_in_train(train_path, remove_old_versions)
    except TrainNotFound:
        print(f'[\033[91mFAILED\x1B[0m]\tSpecified {train_path!r} path does not exist')
        exit(1)

    if summary['upgraded']:
        print('[\033[92mOK\x1B[0m]\tFollowing item(s) were upgraded successfully:')
        upgraded = summary['upgraded']
        for index, item in enumerate(upgraded):
            print(f'[\033[92mOK\x1B[0m]\t{index + 1}) {item} (new version is {upgraded[item]["new_version"]})')
    else:
        print('[\033[91mFAILED\x1B[0m]\tNo item(s) were upgraded')
    return summary


@functools.cache
def get_config() -> dict:
    config = {
        **(dotenv_values('.env') if os.path.exists('.env') else {}),
        **os.environ,
        'GITHUB_TOKEN': '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',
    }
    config.setdefault('GITHUB_BASE', 'automated-updates')
    return config


def validate_config() -> None:
    try:
        json_schema_validate({
            'type': 'object',
            'properties': {
                'GITHUB_TOKEN': {'type': 'string'},
                'GITHUB_BASE': {'type': 'string'},
            },
            'required': ['GITHUB_TOKEN'],
        }, get_config())
    except JsonValidationError as e:
        print(f'[\033[91mFAILED\x1B[0m]\tInvalid configuration specified for pushing changes: {e}')
        exit(1)


def push_changes_upstream(train_path: str, summary: dict, branch: str) -> None:
    try:
        config = get_config()
        message = textwrap.dedent(f'''
        Upgraded catalog item(s)

        This commit upgrades {", ".join(summary["upgraded"])} catalog item(s).
        ''')
        commit_changes(train_path, message)
        push_changes(train_path, config['GITHUB_TOKEN'], branch, config.get('GITHUB_ORIGIN'))
        create_pull_request(train_path, branch, config)
    except Exception as e:
        print(f'[\033[91mFAILED\x1B[0m]\tFailed to create a PR with upgraded item versions: {e}')
        exit(1)


def checkout_update_repo(path: str, branch: str) -> None:
    try:
        checkout_branch(path, get_config()['GITHUB_BASE'])
        update_branch(path, get_config()['GITHUB_BASE'])
        checkout_branch(path, branch, True)
    except Exception as e:
        print(f'[\033[91mFAILED\x1B[0m]\tFailed to checkout {branch!r} branch: {e}')
        exit(1)


def main() -> None:
    # TODO: Improve git commit/push workflow allowing more customization in next cycle
    parser = argparse.ArgumentParser(prog='catalog_update')
    subparsers = parser.add_subparsers(help='sub-command help', dest='action')

    update = subparsers.add_parser(
        'update', help='Update version of catalog item(s) if newer image versions are available'
    )
    update.add_argument('--path', help='Specify path to a valid train of a TrueNAS compliant catalog', required=True)
    update.add_argument(
        '--remove-old-versions', '-r', action='store_true', help='Remove old version of catalog item', default=False
    )
    update.add_argument(
        '--push', '-p', action='store_true', help='Push changes to git repository with provided credentials',
        default=False
    )

    args = parser.parse_args()
    if args.action == 'update':
        branch_name = generate_branch_name()
        if args.push:
            validate_config()
            checkout_update_repo(args.path, branch_name)

        summary = update_items(args.path, args.remove_old_versions)
        if args.push:
            push_changes_upstream(args.path, summary, branch_name)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
