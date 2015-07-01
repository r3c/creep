#!/usr/bin/env python

import ftplib
import itertools
import os
import StringIO

from ..action import Action
from ..path import explode

class FTPTarget:
	def __init__ (self, host, port, user, password, path, options):
		self.host = host or 'localhost'
		self.options = options
		self.port = port or 21
		self.password = password
		self.path = path
		self.user = user

	def connect (self):
		ftp = ftplib.FTP ()
		ftp.connect (self.host, self.port)

		if self.user is not None:
			ftp.login (self.user, self.password)

		if self.path:
			ftp.cwd (self.path)

		ftp.set_pasv (self.options.get ('passive', True))

		return ftp

	def escape (self, path):
		return path # FIXME: wrong escape

	def read (self, logger, path):
		file = StringIO.StringIO ()
		ftp = self.connect ()

		try:
			ftp.retrbinary ('RETR ' + self.escape (path), file.write)

			return file.getvalue ()
		except ftplib.error_perm, e:
			logger.debug (e)

			return None
		finally:
			file.close ()
			ftp.quit ()

	def send (self, logger, work, actions):
		ftp = self.connect ()

		try:
			# Group actions by parent path
			commands = [(head, tail, type) for ((head, tail), type) in ((os.path.split (action.path), action.type) for action in actions)]

			for (directory, files) in itertools.groupby (commands, lambda command: command[0]):
				# Must create directory before uploading files to it
				create = True
				names = explode (directory)

				# Append or delete files
				for (head, tail, type) in files:
					path = self.escape (head and head + '/' + tail or tail)

					if type == Action.ADD:
						# Create missing parent directories
						if create:
							for parent in ('/'.join (names[0:n + 1]) for n in range (0, len (names))):
								try:
									ftp.mkd (parent)
								except ftplib.error_perm, e:
									if not e.message.startswith ('550 '):
										raise e

							create = False

						# Upload current file
						with open (os.path.join (work, head, tail), 'rb') as file:
							ftp.storbinary ('STOR ' + path, file)

					elif type == Action.DEL:
						# Delete file if exists
						try:
							ftp.delete (path)
						except ftplib.error_perm, e:
							if not e.message.startswith ('550 '):
								raise e

		except ftplib.error_perm, e:
			logger.debug (e)

			return False
		finally:
			ftp.quit ()

		return True
