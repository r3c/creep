#!/usr/bin/env python

from ..action import Action
from ..process import Process

class GitSource:
	def __init__ (self, directory):
		self.directory = directory

	def current (self):
		revision = Process (['git', 'rev-parse', '--quiet', '--verify', 'HEAD']).execute ()

		if revision is None:
			return None

		return revision.strip ()

	def diff (self, logger, work, rev_from, rev_to):
		# Parse and validate source and target revisions
		if rev_from is not None:
			hash_from = Process (['git', 'rev-parse', '--quiet', '--verify', rev_from]).execute ()
		else:
			hash_from = Process (['git', 'hash-object', '-t', 'tree', '/dev/null']).execute ()

		if hash_from is None:
			logger.warning ('Invalid source revision "{0}".'.format (rev_from))

			return None

		hash_to = Process (['git', 'rev-parse', '--quiet', '--verify', rev_to]).execute ()

		if hash_to is None:
			logger.warning ('Invalid target revision "{0}".'.format (rev_to))

			return None

		hash_from = hash_from.strip ()
		hash_to = hash_to.strip ()

		# Display update information
		if hash_from != hash_to:
			logger.info ('Update from revision ((fuchsia)){0}((reset)) to ((fuchsia)){1}((reset))...'.format (hash_from[0:8], hash_to[0:8]))
		else:
			logger.info ('Already at revision ((fuchsia)){0}((reset)).'.format (hash_from[0:8]))

			return []

		# Populate work directory from Git archive
		archive = Process (['git', 'archive', hash_to, '.']).execute ()

		if archive is None or Process (['tar', 'xC', work]).set_stdin (archive).execute () is None:
			logger.warning ('Couldn\'t export archive from Git.')

			return None

		# Build actions from Git diff output
		lines = Process (['git', 'diff', '--name-status', '--relative', hash_from, hash_to]).execute ()

		if lines is None:
			logger.warning ('Couldn\'t get diff from Git.')

			return None

		actions = []

		for line in lines.splitlines ():
			(mode, path) = line.split ('\t', 1)

			if mode == 'A' or mode == 'M':
				actions.append (Action (path, Action.ADD))
			elif mode == 'D':
				actions.append (Action (path, Action.DEL))

		return actions
