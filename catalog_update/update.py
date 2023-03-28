import os

from collections import defaultdict

from .catalog_item import Item
from .exceptions import ValidationErrors, TrainNotFound


def update_items_in_train(train_path: str) -> dict:
    if not os.path.exists(train_path):
        raise TrainNotFound(train_path)

    summary = {
        'skipped': {},
        'upgraded': defaultdict(lambda: {'new_version': None, 'old_version': None, 'item_path': None}),
    }
    for item_path in filter(os.path.isdir, map(lambda i: os.path.join(train_path, i), os.listdir(train_path))):
        item = Item(item_path)
        try:
            item.validate()
        except ValidationErrors:
            summary['skipped'][item.name] = 'Validation failed'
            continue

        info = item.upgrade()
        if not info['upgraded']:
            summary['skipped'][item.name] = info['error']
            continue

        summary['upgraded'][item.name].update({
            'new_version': info['new_version'],
            'old_version': info['latest_version'],
            'item_path': item_path,
        })

    return summary
