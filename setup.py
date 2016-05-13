#!/usr/bin/env python

from codecs import open
from os import path
from setuptools import find_packages, setup

import creep

with open (path.join (path.abspath (path.dirname (__file__)), 'README.md'), encoding = 'utf-8') as file:
	long_description = file.read ()

setup(
	name = 'creep',
	version = creep.__version__,
	description = 'Incremental FTP/SSH deployment tool',
	long_description = long_description,
	url = 'https://github.com/r3c/creep',
	author = 'Remi Caput',
	author_email = 'python.org+creep@mirari.fr',
	license = 'MIT',
	keywords = 'deploy deployment incremetal ftp ssh git',
	classifiers = [
		'Development Status :: 4 - Beta',
		'Environment :: Console',
		'Intended Audience :: Developers',
		'Intended Audience :: System Administrators',
		'License :: OSI Approved :: MIT License',
		'Programming Language :: Python :: 2.7',
		'Topic :: Software Development :: Build Tools',
		'Topic :: System :: Archiving :: Mirroring',
		'Topic :: System :: Software Distribution'
	],
	install_requires = ['setuptools>=1.0'],
	packages = [
		'creep',
		'creep.src',
		'creep.src.sources',
		'creep.src.targets'
	],
	entry_points = {
		'console_scripts':	['creep = creep.creep:main']
	}
)
