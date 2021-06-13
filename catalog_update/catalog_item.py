import json
import os


from catalog_validation.validation import validate_catalog_item
from typing import Optional


class Item:
    def __init__(self, path: str):
        self.path = path

    @property
    def exists(self) -> bool:
        return os.path.exists(self.path)

    @property
    def upgrade_info_path(self) -> str:
        return os.path.join(self.path, 'upgrade_info.json')

    @property
    def upgrade_info_defined(self) -> bool:
        return os.path.isfile(self.upgrade_info_path)

    def validate(self) -> None:
        validate_catalog_item(self.path, 'catalog_update')

    def upgrade_info(self) -> Optional[dict]:
        if not self.upgrade_info_defined:
            return

        with open(self.upgrade_info_path, 'r') as f:
            return json.loads(f.read())
