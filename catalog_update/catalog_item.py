import json
import os
import subprocess


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
        return os.path.join(self.path, 'upgrade_info')

    @property
    def upgrade_strategy_defined(self) -> bool:
        return os.path.isfile(self.upgrade_info_path) and os.access(self.upgrade_info_path, os.X_OK)

    def validate(self) -> None:
        validate_catalog_item(self.path, 'catalog_update')

    def upgrade_info(self) -> Optional[dict]:
        if not self.upgrade_strategy_defined:
            return

        cp = subprocess.Popen(self.upgrade_info_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = cp.communicate()
        if cp.returncode:
            raise subprocess.CalledProcessError(cp.returncode, cp.args, stderr=stderr)

        return json.loads(stdout)
