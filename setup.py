#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

from setuptools import setup, find_packages

setup(name='hwtLib',
      version='0.1',
      description='library of hardware components and test for hwtoolkit framework',
      url='https://github.com/Nic30/hwtLib',
      author='Michal Orsak',
      author_email='michal.o.socials@gmail.com',
      install_requires=[
        'hwtLib',
        'Pillow', # there is code which isreading images
      ],
      license='MIT',
      packages = find_packages(),
      package_data={'hwtLib': ['*.vhd', '*.v', '.png']},
      include_package_data=True,
      zip_safe=False)
