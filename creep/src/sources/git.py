#!/usr/bin/env python

from ..action import Action
from ..process import Process

class GitSource:
	def __init__ (self, directory):
		self.directory = directory

	def current (self):
		revision = Process (['git', 'rev-parse', '--quiet', '--verify', 'HEAD']).execute ()

		if revision:
			return revision.out.strip ()

		return None

	def diff (self, logger, work, rev_from, rev_to):
		# Parse and validate source and target revisions
		if rev_from is not None:
			res_from = Process (['git', 'rev-parse', '--quiet', '--verify', rev_from]).execute ()
		else:
			res_from = Process (['git', 'hash-object', '-t', 'tree', '/dev/null']).execute ()

		if not res_from:
			logger.warning ('Invalid source revision "{0}".'.format (rev_from))
			logger.debug (res_from.err)

			return None

		res_to = Process (['git', 'rev-parse', '--quiet', '--verify', rev_to]).execute ()

		if not res_to:
			logger.warning ('Invalid target revision "{0}".'.format (rev_to))
			logger.debug (res_to.err)

			return None

		hash_from = res_from.out.strip ()
		hash_to = res_to.out.strip ()

		# Display update information
		if hash_from != hash_to:
			logger.info ('Update from revision ((fuchsia)){0}((reset)) to ((fuchsia)){1}((reset))...'.format (hash_from[0:8], hash_to[0:8]))
		else:
			logger.info ('Already at revision ((fuchsia)){0}((reset)).'.format (hash_from[0:8]))

			return []

		# Populate work directory from Git archive
		archive = Process (['git', 'archive', hash_to, '.']).pipe (['tar', 'xC', work]).execute ()

		if not archive:
			logger.warning ('Couldn\'t export archive from Git.')
			logger.debug (archive.err)

			return None

		# Build actions from Git diff output
		diff = Process (['git', 'diff', '--name-status', '--relative', hash_from, hash_to]).execute ()

		if not diff:
			logger.warning ('Couldn\'t get diff from Git.')
			logger.debug (diff.err)

			return None

		actions = []

		for line in diff.out.splitlines ():
			(mode, path) = line.split ('\t', 1)

			if mode == 'A' or mode == 'M':
				actions.append (Action (path, Action.ADD))
			elif mode == 'D':
				actions.append (Action (path, Action.DEL))

		return actions
