#!/usr/bin/env python

import logging
import re

class LoggerColorStreamHandler (logging.StreamHandler):
	COLOR_BEGIN = '(('
	COLOR_END = '))'
	RESET = '\033[0m'

	def __init__ (self, *args, **kwargs):
		super (LoggerColorStreamHandler, self).__init__ (*args, **kwargs)

		self.colors = {
			'black':	'\033[0;30m',
			'maroon':	'\033[0;31m',
			'green':	'\033[0;32m',
			'olive':	'\033[0;33m',
			'navy':		'\033[0;34m',
			'purple':	'\033[0;35m',
			'teal':		'\033[0;36m',
			'silver':	'\033[0;37m',
			'grey':		'\033[1;30m',
			'red':		'\033[1;31m',
			'lime':		'\033[1;32m',
			'yellow':	'\033[1;33m',
			'blue':		'\033[1;34m',
			'fuchsia':	'\033[1;35m',
			'cyan':		'\033[1;36m',
			'white':	'\033[1;37m',
			'reset':	self.RESET
		}

		self.end = getattr (self, 'terminator', '\n')
		self.levels = {logging.CRITICAL: 'red', logging.DEBUG: 'olive', logging.ERROR: 'red', logging.INFO: 'white', logging.WARNING: 'yellow'}
		self.tags = re.compile (re.escape (self.COLOR_BEGIN) + '([0-9A-Za-z_]+)' + re.escape (self.COLOR_END))

	def is_tty (self):
		isatty = getattr (self.stream, 'isatty', None)

		return isatty and isatty ()

	def emit (self, record):
		try:
			message = self.format (record)
			stream = self.stream

			if self.is_tty ():
				message = self.COLOR_BEGIN + self.levels.get (record.levelno, 'reset') + self.COLOR_END + message + self.RESET
				message = self.tags.sub (lambda m: self.colors.get (m.group (1), self.RESET), message)
			else:
				message = self.tags.sub ('', message)

			stream.write (message)
			stream.write (self.end)

			self.flush ()

		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			self.handleError (record)

class Logger:
	@staticmethod
	def build ():
		formatter = logging.Formatter ('%(levelname)s: %(message)s')

		console = LoggerColorStreamHandler ()
		console.setFormatter (formatter)

		logger = logging.getLogger ()
		logger.addHandler (console)

		return logger
