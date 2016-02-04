#!/usr/bin/python
from setuptools import setup
from cachefs import __version__

setup (name = 'cachefs',
        version = __version__,
        install_requires = [
            'pyat',
        ],
	packages = [
            'cachefs',
        ],
)
