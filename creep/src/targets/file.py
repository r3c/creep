#!/usr/bin/env python

import os
import shutil

from .. import path

class FileTarget:
	def __init__ (self, directory):
		self.directory = directory

	def read (self, logger, relative):
		source = os.path.join (self.directory, relative)

		if not os.path.isfile (source):
			return ''

		if not os.access (source, os.R_OK):
			return None

		with open (source, 'rb') as file:
			return file.read ()

	def send (self, logger, work, actions):
		for action in actions:
			if action.type == action.ADD:
				path.duplicate (action.path, self.directory, action.path)

			elif action.type == action.DEL:
				target = os.path.join (self.directory, action.path)

				if os.path.isfile (target):
					os.remove (target)

		return True
