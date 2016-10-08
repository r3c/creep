#!/usr/bin/env python

import os
import shutil

from .. import path

class FileTarget:
	def __init__ (self, directory):
		self.directory = directory

	def read (self, logger, relative):
		if not os.path.isdir (self.directory):
			logger.warning ('Directory "{0}" doesn\'t exist'.format (self.directory))

			return None

		source = os.path.join (self.directory, relative)

		if not os.path.isfile (source):
			logger.debug ('Revision file "{0}" doesn\'t exist'.format (source))

			return ''

		if not os.access (source, os.R_OK):
			logger.warning ('Revision file "{0}" cannot be read'.format (source))

			return None

		with open (source, 'rb') as file:
			return file.read ()

	def send (self, logger, work, actions):
		for action in actions:
			if action.type == action.ADD:
				if not path.duplicate (os.path.join (work, action.path), self.directory, action.path):
					logger.warning ('Can\'t copy file "{1}" to target directory "{0}"'.format (self.directory, action.path))

			elif action.type == action.DEL:
				if not path.remove (self.directory, action.path):
					logger.warning ('Can\'t remove file "{1}" from target directory "{0}"'.format (self.directory, action.path))

		return True
