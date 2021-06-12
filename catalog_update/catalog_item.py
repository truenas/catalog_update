import os


from catalog_validation.validation import validate_catalog_item


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
