import json
import subprocess


DEFAULT_DOCKER_REGISTRY = 'docker.io'
DEFAULT_DOCKER_REPO = 'library'
DEFAULT_DOCKER_TAG = 'latest'


def parse_image_tag(tag: str) -> dict[str, str]:
    # Following logic has been used from docker engine to make sure we follow the same rules/practices
    # for normalising the image name / tag
    i = tag.find('/')
    if i == -1 or (not any(c in tag[:i] for c in ('.', ':')) and tag[:i] != 'localhost'):
        registry, image_tag = DEFAULT_DOCKER_REGISTRY, tag
    else:
        registry, image_tag = tag[:i], tag[i + 1:]

    if '/' not in image_tag:
        image_tag = f'{DEFAULT_DOCKER_REPO}/{image_tag}'

    if ':' not in image_tag:
        image_tag += f':{DEFAULT_DOCKER_TAG}'

    image_str, tag_str = image_tag.rsplit(':', 1)
    return {
        'image': image_str,
        'tag': tag_str,
        'registry': registry,
        'complete_tag': f'{registry}/{image_str}:{tag_str}',
    }


def get_image_tags(image_name: str) -> dict:
    image_details = parse_image_tag(image_name)
    cp = subprocess.Popen(
        ['skopeo', 'list-tags', '--no-creds', f'docker://{image_details["registry"]}/{image_details["image"]}'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = cp.communicate()
    if cp.returncode:
        raise subprocess.CalledProcessError(cp.returncode, cp.args, stderr=stderr)

    return json.loads(stdout)
