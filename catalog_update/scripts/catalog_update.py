#!/usr/bin/env python
import argparse
import os

from catalog_update.exceptions import TrainNotFound
from catalog_update.update import update_items_in_train
from dotenv import dotenv_values


def update_items(train_path: str, remove_old_versions: bool) -> None:

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


def main() -> None:
    config = {
        **(dotenv_values('.env') if os.path.exists('.env') else {}),
        **os.environ,
    }

    parser = argparse.ArgumentParser(prog='catalog_update')
    subparsers = parser.add_subparsers(help='sub-command help', dest='action')

    update = subparsers.add_parser(
        'update', help='Update version of catalog item(s) if newer image versions are available'
    )
    update.add_argument('--path', help='Specify path to a valid train of a TrueNAS compliant catalog', required=True)
    update.add_argument(
        '--remove-old-versions', '-r', action='store_true', help='Remove old version of catalog item', default=False
    )

    args = parser.parse_args()
    if args.action == 'update':
        update_items(args.path, args.remove_old_versions)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
