#!/usr/bin/env python

import json

class Revision:
	def __init__ (self, data):
		states = {}	

		if data != '':
			for (name, rev) in json.loads (data).iteritems ():
				states[name] = rev

		self.states = states

	def get (self, name):
		return self.states.get (name, None)

	def serialize (self):
		return json.dumps (self.states, indent = 4, sort_keys = True)

	def set (self, name, data):
		self.states[name] = data
