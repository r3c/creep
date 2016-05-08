#!/usr/bin/env python

import json
import os

class EnvironmentConfig:
	def __init__ (self, config):
		self.connection = config['connection']
		self.diff = config.get ('diff', None)
		self.local = config.get ('local', False)
		self.options = config.get ('options', {})
		self.state = config.get ('state', '.creep.revs')

class Environments:
	def __init__ (self, path):
		envs = {}

		if os.path.isfile (path):
			try:
				with open (path, 'rb') as stream:
					for (name, env) in json.load (stream).iteritems ():
						envs[name] = EnvironmentConfig (env)

			except KeyError, key:
				raise ValueError ('missing property "{0}" in environments file "{1}"'.format (key, path))

		self.envs = envs

	def get (self, name):
		return self.envs.get (name, None)
