#!/usr/bin/env python

import os

def explode (path):
	names = []

	while path != '' and path != '/':
		(path, tail) = os.path.split (path)

		if tail != '':
			names.insert (0, tail)

	if path == '/':
		names.insert (0, path)

	return names
