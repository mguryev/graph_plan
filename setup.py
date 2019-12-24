#! /usr/bin/env python3

from setuptools import setup

setup(
    name='graph_plan',
    version='0.1',
    description='A useful module',

    author='Max Guriev',
    author_email='mguryev@gmail.com',

    packages=['graph_plan'],

    install_requires=[
        'attrs',
    ],

    tests_require=[
        'pytest',
    ]
)
