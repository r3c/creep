#!/usr/bin/env python

import ftplib
import io
import itertools
import os

from ..action import Action
from ..path import explode

class FTPTarget:
	def __init__ (self, host, port, user, password, directory, options):
		self.directory = directory
		self.host = host or 'localhost'
		self.options = options
		self.port = port or 21
		self.password = password
		self.user = user

	def connect (self, logger):
		ftp = ftplib.FTP ()
		ftp.connect (self.host, self.port)

		try:
			if self.user is not None:
				ftp.login (self.user, self.password)

			if self.directory:
				ftp.cwd (self.directory)

			ftp.set_pasv (self.options.get ('passive', True))
		except ftplib.all_errors as e:
			if e.message.startswith ('530 '):
				logger.debug ('Can\'t authenticate as \'{0}\' on remote FTP: \'{1}\''.format (self.user, e.message))
			elif e.message.startswith ('550 '):
				logger.debug ('Can\'t access folder \'{0}\' on remote FTP: \'{1}\''.format (self.directory, e.message))
			else:
				logger.debug ('Unknown FTP error: \'{0}\''.format (e.message))

			ftp.quit ()

			return None

		return ftp

	def escape (self, path):
		return path # FIXME: wrong escape [ftp-escape]

	def read (self, logger, path):
		ftp = self.connect (logger)

		if ftp is None:
			return None

		with io.BytesIO () as buffer:
			try:
				ftp.retrbinary ('RETR ' + self.escape (path), buffer.write)

				return buffer.getvalue ()

			except ftplib.all_errors as e:
				if e.message.startswith ('550 '): # no such file or directory
					return ''

				logger.debug ('Can\'t read file from FTP remote: {0}'.format (e.message))

				return None

			finally:
				ftp.quit ()

	def send (self, logger, work, actions):
		ftp = self.connect (logger)

		if ftp is None:
			return None

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
								except ftplib.all_errors as e:
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
						except ftplib.all_errors as e:
							if not e.message.startswith ('550 '):
								raise e

		except ftplib.all_errors as e:
			logger.debug ('Can\'t deploy to FTP remote: {0}'.format (e.message))

			return False

		finally:
			ftp.quit ()

		return True
