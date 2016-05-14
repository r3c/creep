#!/usr/bin/env python

import re
import urllib

class Target:
	@staticmethod
	def build (logger, connection, options):
		# FIXME: should use urllib.parse [url-parse]
		match = re.match ('([+0-9A-Za-z]+)://(?:([^#/:@]+)(?::([^#/@]+))?@)?(?:([^#/:]+)(?::([0-9]+))?)?(?:/([^#]*))?', connection)

		if match is None:
			return None

		directory = match.group (6) or '.'
		host = match.group (4)
		password = match.group (3) is not None and urllib.unquote_plus (match.group (3)) or match.group (3)
		port = match.group (5) is not None and int (match.group (5)) or None
		scheme = match.group (1)
		user = match.group (2) is not None and urllib.unquote_plus (match.group (2)) or match.group (2)

		if scheme == 'file':
			if host is not None or password is not None or port is not None or user is not None:
				logger.warn ('Connection string for "file" scheme shouldn\'t contain any host, port, user or password.')

			from targets.file import FileTarget

			return FileTarget (directory)

		if scheme == 'ftp':
			from targets.ftp import FTPTarget

			return FTPTarget (host, port, user, password, directory, options)

		if scheme == 'ssh':
			if password is not None:
				logger.warn ('Connection string for "ssh" scheme shouldn\'t contain any password.')

			from targets.ssh import SSHTarget

			return SSHTarget (host, port, user, directory, options)

		# No known scheme recognized
		return None
