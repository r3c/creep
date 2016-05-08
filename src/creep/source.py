#!/usr/bin/env python

import os

from path import explode

def build (diff, directory):
	diff = diff or detect (directory)

	if diff == 'delta':
		from sources.delta import DeltaSource

		return DeltaSource (directory)

	if diff == 'git':
		from sources.git import GitSource

		return GitSource (directory)

	# No known diff type recognized
	return None

def detect (directory):
	names = explode (directory)

	# Detect '.git' directory in parent folders
	if any ((os.path.exists (os.path.join (*(names[0:n] + ['.git']))) for n in range (len (names), 0, -1))):
		return 'git'

	# Fallback to delta diff by default
	return 'delta'
