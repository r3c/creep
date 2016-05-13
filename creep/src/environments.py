#!/usr/bin/env python

import json
import os

class EnvironmentLocation:
	def __init__ (self, location):
		self.connection = location['connection']
		self.local = location.get ('local', False)
		self.options = location.get ('options', {})
		self.state = location.get ('state', '.creep.revs')

class Environments:
	def __init__ (self, logger, path):
		# Load environments configuration from file if available...
		if os.path.isfile (path):
			try:
				with open (path, 'rb') as stream:
					config = json.load (stream)

			except KeyError, key:
				raise ValueError ('missing property "{0}" in environments file "{1}"'.format (key, path))

		# ...or use empty configuration otherwise
		else:
			config = {}

		# Compatibility mode: update to new format if no "locations" key found
		if len (config) > 0 and not 'locations' in config and not 'options' in config and not 'source' in config:
			logger.warn ('Your environments file seems to be using deprecated format, please consider updating it.')

			config = {'locations': config}

		self.locations = dict (((name, EnvironmentLocation (location)) for (name, location) in config.get ('locations', {}).iteritems ()))
		self.options = config.get ('options', {})
		self.source = config.get ('source', None)

	def get_location (self, name):
		return self.locations.get (name, None)
