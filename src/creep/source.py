#!/usr/bin/env python

import os

from path import explode

def build (delta, directory):
	delta = delta or detect (directory)

	if delta == 'file':
		from sources.file import FileSource

		return FileSource (directory)

	if delta == 'git':
		from sources.git import GitSource

		return GitSource (directory)

	# No known delta type recognized
	return None

def detect (directory):
	names = explode (directory)

	# Detect '.git' directory in parent folders
	if any ((os.path.exists (os.path.join (*(names[0:n] + ['.git']))) for n in range (len (names), 0, -1))):
		return 'git'

	# Fallback to file delta
	return 'file'
