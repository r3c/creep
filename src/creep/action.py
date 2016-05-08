#!/usr/bin/env python

class Action:
	ADD = 1
	DEL = 2
	ERR = 3
	NOP = 4

	def __init__ (self, path, type):
		self.path = path
		self.type = type
