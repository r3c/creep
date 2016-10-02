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
	if not os.path.isdir (base):
		return False

	destination = os.path.join (base, target)
	directory = os.path.dirname (destination)

	if not os.path.isdir (directory):
		os.makedirs (directory)

	shutil.copy (source, destination)

	return True

"""
Explode path into separate components.
path:	input path
return:	path components
"""
def explode (path):
	names = []
	tail = '.'

	while tail != '':
		(path, tail) = os.path.split (path)

		if tail != '':
			names.insert (0, tail)
		elif path != '':
			names.insert (0, path)

	return names

"""
Remove file from given directory if exists.
base:	base directory of target file
target:	path to target file relative to base directory
"""
def remove (base, target):
	remove = os.path.join (base, target)

	if not os.path.isfile (remove):
		return False

	os.remove (remove)

	return True
