#!/usr/bin/env python

class Action:
	ADD = 0
	DEL = 1
	ERR = 2	
	NOP = 3

	def __init__ (self, path, type):
		self.path = path
		self.type = type
