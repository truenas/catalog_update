# Automated Updates For Catalog Item(s)

Catalog item(s) usually do not allow image version tags to be specified explicitly by the user which results in
frequent upgrades for catalog item(s) whenever a newer upstream image tag is available. `catalog_update` is designed
to allow automated upgrades of catalog item(s) where if the catalog item conforms to `catalog_update` required format,
`catalog_update` will upgrade the version of the item with the newer available image tag.


## Usage

Catalog can be updated with the following command
```
docker run --rm -it -e GITHUB_TOKEN="token_here" -e GITHUB_USERNAME="git_handle_here" -e GITHUB_EMAIL="git_email_here" -v /charts:/catalog ixsystems/catalog_update
```

Following environment variables are required:
1. GITHUB_TOKEN
2. GITHUB_USERNAME
3. GITHUB_EMAIL

These environment variables will be used to push the changes to github.

## Catalog Item Structure

In order for automated update(s) for the catalog item to work, catalog item should comply with the following structure:

```
plex
├── 1.6.0
│   ├── CHANGELOG.md
│   ├── Chart.lock
│   ├── Chart.yaml
│   ├── README.md
│   ├── app-readme.md
│   ├── charts
│   │   └── common-2101.0.0.tgz
│   ├── default_values.yaml
│   ├── ix_values.yaml
│   ├── migrations
│   │   └── migrate_from_1.0.0
│   ├── questions.yaml
│   ├── templates
│   │   ├── NOTES.txt
│   │   ├── deployment.yaml
│   │   ├── probe_config.yaml
│   │   ├── service-tcp.yaml
│   │   └── service-udp.yaml
│   ├── test_values.yaml
│   └── values.yaml
└── item.yaml
└── upgrade_info.json
└── upgrade_strategy
```

New files in the catalog item are:

#### 1. `upgrade_info.json`

`upgrade_info.json` should be a json file which should contain a valid dictionary ( json object ) having the following
format:

```
{
    "filename": "ix_values.yaml",
    "keys": [
        "image",
        "debian.image"
    ],
    "test_filename": "test_values.yaml"
}
```

`filename` will be the name of the values file where `catalog_update` should lookout for getting current image
tag versions. It should be a valid yaml file which would contain values for the helm chart of the catalog item.

`keys` is a list of keys which `catalog_update` should look out for retrieving image configuration(s) and then checking
if an update is available. Let's consider the following example:

```
image:
  repository: ghcr.io/chia-network/chia
  tag: 1.1.6
  pullPolicy: IfNotPresent
updateStrategy: Recreate
debian:
  image:
    repository: debian
    tag: latest
    pullPolicy: IfNotPresent
```

The above values yaml file contains 2 images references and if we would like `catalog_update` to check for updates
for both tags, we would refer to both keys in `upgrade_info.json` i.e `image` and `postgres.image`, nested
dictionary keys are separated by `.`.

For some catalog(s) which is using CI to validate the changed item version(s), it's possible that they have another
values file which is only used in the CI. In such cases, the name of the test file can be specified and `catalog_update`
would look for the same keys as it did for `filename` and update the relevant keys with the newer image tags.

#### 2. `upgrade_strategy`

`upgrade_strategy` is an executable file which should accept the following format as input via stdin:

```
{
    "image": [
        "1.0rc9",
        "1.0.0",
        "1.0.1",
        "1.0.2",
        "unstable",
        "1.0.3",
        "1.0.4",
        "1.0.5",
        "1.1.0",
        "1.1.1",
        "1.1.2",
        "1.1.3",
        "1.1.4",
        "1.1.6",
        "1.1.7",
        "latest"
    ],
    "debian.image": [
        "unstable-slim",
        "stable-slim",
        "latest",
        "testing"
    ]
}
```

Each key of the dictionary would be taken from the `keys` specified earlier in `upgrade_info.json` and if for some
key `catalog_update` is not able to retrieve image tags, the key would be present in the above input but would contain
an empty list.

`upgrade_strategy` should return a valid json dictionary containing the key name from `upgrade_info.json` and the
latest available image tag for the image. If `upgrade_strategy` does not return all the tags specified in
`upgrade_info.json`, they are ignored by `catalog_update` and only specified ones are then accounted for.

An example of output would be:

```
{
    "app_version": "newversionhere",
    "tags": {
        "image": "1.1.7",
        "debian.image": "unstable"
    }
}
```

If `app_version` is optional and if provided, the provided version would be used for the newer catalog item version.
