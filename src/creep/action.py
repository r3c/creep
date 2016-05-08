#!/usr/bin/env python

import os
import shutil

class Action:
	ADD = 1
	DEL = 2
	ERR = 3
	NOP = 4

	def __init__ (self, path, type):
		self.path = path
		self.type = type

	def prepare (self, work):
		if self.type == Action.ADD:
			target = os.path.join (work, self.path)
			directory = os.path.dirname (target)

			if not os.path.isdir (directory):
				os.makedirs (directory)

			shutil.copy (self.path, target)
