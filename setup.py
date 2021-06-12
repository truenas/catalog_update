from distutils.core import setup
from setuptools import find_packages

VERSION = '0.1'

setup(
    name='catalog_update',
    description='Automated updates of TrueNAS SCALE compliant Catalog(s)',
    version=VERSION,
    include_package_data=True,
    packages=find_packages(),
    license='GNU3',
    platforms='any',
)
