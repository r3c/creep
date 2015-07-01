#!/usr/bin/env python

import os

from path import explode

def build (directory):
	# Detect '.git' directory in parent folders
	names = explode (directory)

	if any ((os.path.exists (os.path.join (*(names[0:n] + ['.git']))) for n in range (len (names), 0, -1))):
		from sources.git import GitSource

		return GitSource (directory)

	# No known source type recognized
	return None
