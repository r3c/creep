#!/usr/bin/env python

from ..action import Action
from ..process import Process

class GitSource:
	def current (self, base_path):
		revision = Process (['git', 'rev-parse', '--quiet', '--verify', 'HEAD']) \
			.set_directory (base_path) \
			.execute ()

		if revision:
			return revision.out.decode ('utf-8').strip ()

		return None

	def diff (self, logger, base_path, work_path, rev_from, rev_to):
		# Parse and validate source and target revisions
		if rev_from is not None and rev_from != '':
			process = Process (['git', 'rev-parse', '--quiet', '--verify', rev_from])
		else:
			process = Process (['git', 'hash-object', '-t', 'tree', '/dev/null'])

		res_from = process \
			.set_directory (base_path) \
			.execute ()

		if not res_from:
			logger.warning ('Invalid source revision "{0}".'.format (rev_from))
			logger.debug (res_from.err.decode ('utf-8'))

			return None

		res_to = Process (['git', 'rev-parse', '--quiet', '--verify', rev_to]) \
			.set_directory (base_path) \
			.execute ()

		if not res_to:
			logger.warning ('Invalid target revision "{0}".'.format (rev_to))
			logger.debug (res_to.err.decode ('utf-8'))

			return None

		hash_from = res_from.out.decode ('utf-8').strip ()
		hash_to = res_to.out.decode ('utf-8').strip ()

		# Display update information
		if hash_from != hash_to:
			logger.info ('Update from revision ((fuchsia)){0}((reset)) to ((fuchsia)){1}((reset))...'.format (hash_from[0:8], hash_to[0:8]))
		else:
			logger.info ('Already at revision ((fuchsia)){0}((reset)).'.format (hash_from[0:8]))

			return []

		# Populate work directory from Git archive
		archive = Process (['git', 'archive', hash_to, '.']) \
			.set_directory (base_path) \
			.pipe (['tar', 'xC', work_path]) \
			.execute ()

		if not archive:
			logger.warning ('Couldn\'t export archive from Git.')
			logger.debug (archive.err.decode ('utf-8'))

			return None

		# Build actions from Git diff output
		diff = Process (['git', 'diff', '--name-status', '--relative', hash_from, hash_to]) \
			.set_directory (base_path) \
			.execute ()

		if not diff:
			logger.warning ('Couldn\'t get diff from Git.')
			logger.debug (diff.err.decode ('utf-8'))

			return None

		actions = []

		for line in diff.out.decode ('utf-8').splitlines ():
			(mode, path) = line.split ('\t', 1)

			if mode == 'A' or mode == 'M':
				actions.append (Action (path, Action.ADD))
			elif mode == 'D':
				actions.append (Action (path, Action.DEL))

		return actions
