#!/usr/bin/env python

import os
import shutil

"""
Copy file and create parent directories if needed.
source:	path to source file
base:	base directory of target file (won't be created)
target:	path to target file relative to base directory (will be created)
"""
def duplicate (source, base, target):
	destination = os.path.join (base, target)
	directory = os.path.dirname (destination)

	if not os.path.isdir (directory):
		os.makedirs (directory)

	shutil.copy (source, destination)

def explode (path):
	names = []

	while path != '' and path != '/':
		(path, tail) = os.path.split (path)

		if tail != '':
			names.insert (0, tail)

	if path == '/':
		names.insert (0, path)

	return names
