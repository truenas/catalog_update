#!/usr/bin/env python
import argparse
import functools
import os
import textwrap

from catalog_update.exceptions import TrainNotFound
from catalog_update.git_utils import (
    create_pull_request, checkout_branch, checkout_and_update_branch, commit_changes, generate_branch_name, push_changes
)
from catalog_update.update import update_items_in_train
from dotenv import dotenv_values
from jsonschema import validate as json_schema_validate, ValidationError as JsonValidationError


def update_items(catalog_path: str, train_name: str) -> dict:
    print(f'[\033[92mOK\x1B[0m]\tLooking to update catalog item(s) in {train_name!r} train')
    train_path = os.path.join(catalog_path, train_name)
    try:
        summary = update_items_in_train(train_path)
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
    }
    config.setdefault('GITHUB_BASE', 'master')
    config.setdefault('GITHUB_USERNAME', 'sonicaj')
    config.setdefault('GITHUB_EMAIL', 'waqarsonic1@gmail.com')
    config.setdefault('GITHUB_REVIEWER', ['sonicaj', 'stavros-k'])
    return config


def validate_config() -> None:
    try:
        json_schema_validate({
            'type': 'object',
            'properties': {
                'GITHUB_TOKEN': {'type': 'string'},
                'GITHUB_BASE': {'type': 'string'},
                'GITHUB_USERNAME': {'type': 'string'},
                'GITHUB_EMAIL': {'type': 'string'},
                'GITHUB_REVIEWER': {'type': 'array'},
            },
            'required': ['GITHUB_TOKEN', 'GITHUB_EMAIL', 'GITHUB_USERNAME'],
        }, get_config())
    except JsonValidationError as e:
        print(f'[\033[91mFAILED\x1B[0m]\tInvalid configuration specified for pushing changes: {e}')
        exit(1)


def push_changes_upstream(catalog_path: str, upgraded_apps: list, branch: str) -> None:
    print('[\033[92mOK\x1B[0m]\tPushing changed items upstream')
    try:
        config = get_config()
        message = textwrap.dedent(f'''Upgraded catalog item(s)

        This commit upgrades {", ".join(upgraded_apps)} catalog item(s).
        ''')
        commit_changes(catalog_path, message, config['GITHUB_USERNAME'], config['GITHUB_EMAIL'])
        push_changes(catalog_path, config['GITHUB_TOKEN'], branch, config.get('GITHUB_ORIGIN'))
        print('[\033[92mOK\x1B[0m]\tCreating a PR')
        create_pull_request(
            catalog_path, config['GITHUB_BASE'], branch, config['GITHUB_REVIEWER'], {
                k: v for k, v in config.items() if k != 'GITHUB_REVIEWER'
            }
        )
    except Exception as e:
        print(f'[\033[91mFAILED\x1B[0m]\tFailed to create a PR with upgraded item versions: {e}')
        exit(1)
    else:
        print('[\033[92mOK\x1B[0m]\tSuccessfully created PR')


def checkout_update_repo(path: str, branch: str) -> None:
    print(f'[\033[92mOK\x1B[0m]\tChecking out {branch!r}')
    try:
        checkout_and_update_branch(path, get_config()['GITHUB_BASE'])
        checkout_branch(path, branch, True)
    except Exception as e:
        print(f'[\033[91mFAILED\x1B[0m]\tFailed to checkout {branch!r} branch: {e}')
        exit(1)


def update_trains(catalog_path: str, push: bool) -> None:
    branch_name = generate_branch_name()
    repo_path = catalog_path.replace('/library/ix-dev', '')
    checkout_update_repo(repo_path, branch_name)
    upgraded_apps = []
    for train in filter(lambda path: os.path.isdir(os.path.join(catalog_path, path)), os.listdir(catalog_path)):
        upgraded_apps.extend(update_items(catalog_path, train)['upgraded'].keys())

    if push and upgraded_apps:
        validate_config()
        push_changes_upstream(repo_path, upgraded_apps, branch_name)
    else:
        print('[\033[91mNo Items upgraded\x1B[0m]')


def main() -> None:
    # TODO: Improve git commit/push workflow allowing more customization in next cycle
    parser = argparse.ArgumentParser(prog='catalog_update')
    subparsers = parser.add_subparsers(help='sub-command help', dest='action')

    update = subparsers.add_parser(
        'update', help='Update version of catalog item(s) if newer image versions are available'
    )
    update.add_argument('--path', help='Specify path to a valid TrueNAS compliant catalog', required=True)
    update.add_argument(
        '--push', '-p', action='store_true', help='Push changes to git repository with provided credentials',
        default=False
    )

    args = parser.parse_args()
    if args.action == 'update':
        update_trains(args.path, args.push)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
