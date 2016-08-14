#!/usr/bin/env python

import json

class EnvironmentLocation:
	def __init__ (self, location):
		self.append_files = location.get ('append_files', [])
		self.cascades = dict (((path, isinstance (name, list) and name or [name]) for path, name in location.get ('cascades', location.get ('subsidiaries', {})).iteritems ()))
		self.connection = location.get ('connection', None)
		self.local = location.get ('local', False)
		self.options = location.get ('options', {})
		self.remove_files = location.get ('remove_files', [])
		self.state = location.get ('state', '.creep.rev')

class Environment:
	def __init__ (self, file):
		# Load environments configuration from file
		try:
			config = json.load (file)

		except KeyError, key:
			raise ValueError ('missing property "{0}" in environments file'.format (key))

		self.locations = dict (((name, EnvironmentLocation (location)) for (name, location) in config.iteritems ()))

	def get_location (self, name):
		return self.locations.get (name, None)
