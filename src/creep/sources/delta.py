#!/usr/bin/env python

from ..action import Action
from ..process import Process

class DeltaSource:
	def __init__ (self, directory):
		self.directory = directory

	def current (self):
		raise 'Not implemented'

	def diff (self, logger, work, rev_from, rev_to):
		raise 'Not implemented'
