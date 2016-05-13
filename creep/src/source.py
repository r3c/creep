#!/usr/bin/env python

import os

from path import explode

def build (source, options, directory):
	source = source or detect (directory)

	if source == 'delta' or source == 'hash':
		from sources.hash import HashSource

		return HashSource (directory, options)

	if source == 'git':
		from sources.git import GitSource

		return GitSource (directory)

	# No known source type recognized
	return None

def detect (directory):
	names = explode (directory)

	# Detect '.git' file or directory in parent folders
	if any ((os.path.exists (os.path.join (*(names[0:n] + ['.git']))) for n in range (len (names), 0, -1))):
		return 'git'

	# Fallback to hash source by default
	return 'hash'
