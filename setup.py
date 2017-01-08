#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages, setup

setup_requires = ['setuptools', 'setuptools_git']

setup(
    name="irc2",
    description="irc done right, probably",
    author="Fox Wilson",
    url="https://github.com/fwilson42/irc2",
    version="0.0.1",
    packages=find_packages(),
    test_suite='irc2.ircd.test',
    setup_requires=setup_requires,
    install_requires=setup_requires,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Programming Language :: Python :: 3.5',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
    ],
    keywords=['irc'],
    entry_points={
        'console_scripts': [
            'ircd = irc2.ircd.ircd:main',
        ]
    })
