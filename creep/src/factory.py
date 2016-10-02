#!/usr/bin/env python

from . import path

import os
import re
import urllib

def create_source (source, options, directory):
	source = source or detect (directory)

	if source == 'delta' or source == 'hash':
		from .sources.hash import HashSource

		return HashSource (options)

	if source == 'git':
		from .sources.git import GitSource

		return GitSource ()

	# No known source type recognized
	return None

def create_target (logger, connection, options):
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
		if password is not None or port is not None or user is not None:
			logger.warn ('Connection string for "file" scheme shouldn\'t contain any port, user or password.')

		from .targets.file import FileTarget

		return FileTarget (directory)

	if scheme == 'ftp':
		from .targets.ftp import FTPTarget

		return FTPTarget (host, port, user, password, directory, options)

	if scheme == 'ssh':
		if password is not None:
			logger.warn ('Connection string for "ssh" scheme shouldn\'t contain any password.')

		from .targets.ssh import SSHTarget

		return SSHTarget (host, port, user, directory, options)

	# No known scheme recognized
	return None

def detect (directory):
	drive, tail = os.path.splitdrive (os.path.abspath (directory))
	names = path.explode (tail)

	# Detect '.git' file or directory in parent folders
	if any ((os.path.exists (drive + os.path.join (*(names[0:n] + ['.git']))) for n in range (len (names), 0, -1))):
		return 'git'

	# Fallback to hash source by default
	return 'hash'
