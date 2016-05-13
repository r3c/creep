#!/usr/bin/env python

import os
import pipes
import shlex
import tarfile
import tempfile

from ..action import Action
from ..process import Process

class SSHTarget:
	def __init__ (self, host, port, user, directory, options):
		extra = shlex.split (options.get ('extra', ''))
		remote = str ((user or os.getusername ()) + '@' + (host or 'localhost'))

		self.directory = directory
		self.tunnel = ['ssh', '-T', '-p', str (port or 22)] + extra + [remote]

	def read (self, logger, path):
		command = '! test -f \'{0}\' || cat \'{0}\''.format (pipes.quote (self.directory + '/' + path))

		return Process (self.tunnel + [command]).execute ()

	def send (self, logger, work, actions):
		with tempfile.TemporaryFile () as archive:
			to_add = False
			to_del = []

			# Append files to temporary TAR archive or deletion list
			with tarfile.open (fileobj = archive, mode = 'w') as tar:
				for action in actions:
					if action.type == Action.ADD:
						tar.add (os.path.join (work, action.path), action.path)

						to_add = True
					elif action.type == Action.DEL:
						to_del.append (self.directory + '/' + action.path)

			archive.seek (0)

			# Send and delete files on remote host
			if to_add and Process (self.tunnel + ['tar xC \'' + pipes.quote (self.directory) + '\'']).set_stdin (archive.read ()).execute () is None:
				logger.warning ('Couldn\'t push files to SSH target.')

				return False

			if len (to_del) > 0 and Process (self.tunnel + ['sh']).set_stdin (';'.join (['rm -f \'' + pipes.quote (path) + '\'' for path in to_del])).execute () is None:
				logger.warning ('Couldn\'t delete files from SSH target.')

				return False

		return True
