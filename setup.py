'''Setup script

Usage: pip install .
'''
from setuptools import setup, find_packages

setup(
    name='noobcash',
    version='0.1',
    packages=find_packages(),
    scripts=['manage.py'],
    url='https://github.com/neoaggelos/noobcash',
    author='Aggelos Kolaitis',
    install_requires=[
        'Django', 'pycrypto', 'requests'
    ]
)
