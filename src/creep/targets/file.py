#!/usr/bin/env python

import os
import shutil

class FileTarget:
	def __init__ (self, path):
		self.path = path

	def read (self, logger, path):
		path = os.path.join (self.path, path)

		if not os.path.isfile (path):
			return None

		with open (path, 'rb') as file:
			return file.read ()

	def send (self, logger, work, actions):
		for action in actions:
			path = os.path.join (self.path, action.path)

			if action.type == action.ADD:
				directory = os.path.dirname (path)

				if not os.path.exists (directory):
					os.makedirs (directory)

				shutil.copy (os.path.join (work, action.path), path)

			elif action.type == action.DEL:
				if os.path.isfile (path):
					os.remove (path)

		return True
