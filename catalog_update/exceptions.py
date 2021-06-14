import subprocess

from catalog_validation.exceptions import ValidationErrors, ValidationException  # noqa


class TrainNotFound(ValidationException):
    def __init__(self, train_path):
        super().__init__(f'Unable to locate catalog train at {train_path!r}')


class CalledProcessError(subprocess.CalledProcessError):
    def __str__(self):
        resp = super().__str__()
        return f'{resp} with {self.stderr!r}' if self.stderr else resp
