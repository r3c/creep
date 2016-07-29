#!/usr/bin/env python

import json

class EnvironmentLocation:
	def __init__ (self, name, location):
		self.append_files = location.get ('append_files', [])
		self.connection = location.get ('connection', None)
		self.local = location.get ('local', False)
		self.name = name
		self.options = location.get ('options', {})
		self.remove_files = location.get ('remove_files', [])
		self.state = location.get ('state', '.creep.rev')
		self.subsidiaries = dict (((path, isinstance (name, list) and name or [name]) for path, name in location.get ('subsidiaries', {}).iteritems ()))

class Environment:
	def __init__ (self, file):
		# Load environments configuration from file
		try:
			config = json.load (file)

		except KeyError, key:
			raise ValueError ('missing property "{0}" in environments file'.format (key))

		self.locations = dict (((name, EnvironmentLocation (name, location)) for (name, location) in config.iteritems ()))

	def get_location (self, name):
		return self.locations.get (name, None)
