#!/usr/bin/env python

from ..action import Action

class ConsoleTarget:
	def read (self, logger, path):
		raise Exception ('can\'t read from console target')

	def send (self, logger, work, actions):
		for action in actions:
			if action.type == action.ADD:
				prefix = '((lime))+'
			elif action.type == action.DEL:
				prefix = '((blue))-'
			elif action.type != action.NOP:
				prefix = '((red))!'
			else:
				continue

			logger.info (prefix + '((reset)) ' + action.path)

		return True
