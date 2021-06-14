from typing import Optional
from urllib.parse import urlparse

from .utils import run


def checkout_branch(path: str, branch: str, create: bool = False) -> None:
    flags = []
    if create:
        flags.append('-b')

    run(['git', '-C', path, 'checkout'] + flags + [branch])


def update_branch(path: str, branch: str) -> None:
    run(['git', '-C', path, 'fetch', 'origin'])
    run(['git', '-C', path, 'reset', '--hard', f'origin/{branch}'])


def commit_changes(path: str, commit_msg: str) -> None:
    run(['git', '-C', path, 'add', '.'])
    run(['git', '-C', path, 'commit', '-m', commit_msg])


def push_changes(path: str, api_token: str, branch: str, origin_uri: Optional[None]) -> None:
    url = urlparse(origin_uri or get_origin_uri(path))
    run(['git', '-C', path, 'push', f'https://{api_token}@{url.hostname}{url.path}', branch])


def get_origin_uri(path: str) -> str:
    return run(['git', '-C', path, 'remote', 'get-url', 'origin']).stdout.strip()


def create_pull_request(path: str, config: Optional[dict]) -> None:
    run(f'cd {path} && gh pr create -f', shell=True, env=config)
