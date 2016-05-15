#!/usr/bin/env python

import json
import os
import re

from action import Action
from process import Process

class DefinitionModifier:
	def __init__ (self, regex, filter, rename, modify, link):
		self.filter = filter
		self.link = link
		self.modify = modify
		self.regex = regex
		self.rename = rename

class Definition:
	def __init__ (self, file, ignores):
		modifiers = []

		# Read modifiers from configuration file if available...
		if file is not None:
			config = json.load (file)

			for modifier in config.get ('modifiers', []):
				modify = modifier.get ('modify', modifier.get ('adapt', None))
				filter = modifier.get ('filter', None)
				link = modifier.get ('link', None)
				rename = modifier.get ('rename', modifier.get ('name', None))

				modifiers.append (DefinitionModifier (re.compile (modifier['pattern']), filter, rename, modify, link))

			options = config.get ('options', {})
			source = config.get ('source', None)

		# ...or provide default set of modifiers otherwise
		else:
			options = {}
			source = None

		for ignore in ignores:
			modifiers.append (DefinitionModifier (re.compile ('^' + re.escape (ignore) + '$'), '', None, None, None))

		self.modifiers = modifiers
		self.options = options
		self.source = source

	def apply (self, logger, work, path, type, used):
		# Ensure we don't process a file already scanned
		path = os.path.normpath (path)

		if path in used:
			return ([], [])

		used.add (path)

		# Find modifier matching current file name if any
		name = os.path.basename (path)

		for modifier in self.modifiers:
			match = modifier.regex.search (name)

			if match is None:
				continue

			logger.debug ('File \'{0}\' matches \'{1}\'.'.format (path, modifier.regex.pattern))

			actions = []
			deletes = []

			# Apply renaming pattern if any
			if modifier.rename is not None:
				name = os.path.basename (re.sub ('\\\\([0-9]+)', lambda m: match.group (int (m.group (1))), modifier.rename))

				logger.debug ('File \'{0}\' renamed to \'{1}\'.'.format (path, name))

			path_new = os.path.normpath (os.path.join (os.path.dirname (path), name))

			if type == Action.ADD:
				# Apply link command if any
				if modifier.link is not None:
					out = self.run (work, path, modifier.link)

					if out is not None:
						for link in out.splitlines ():
							logger.debug ('File \'{0}\' is linked to file \'{1}\'.'.format (path, link))

							(actions_append, deletes_append) = self.apply (logger, work, link, type, used)

							actions.extend (actions_append)
							deletes.extend (deletes_append)
					else:
						logger.debug ('Command \'link\' on file \'{0}\' returned non-zero code.'.format (path))

				# Build output file using processing command if any
				if modifier.modify is not None:
					out = self.run (work, path, modifier.modify)

					if out is not None:
						with open (os.path.join (work, path_new), 'wb') as file:
							file.write (out)
					else:
						logger.debug ('Command \'modify\' on file \'{0}\' returned non-zero code.'.format (path))

						type = Action.ERR

					if path != path_new:
						deletes.append (path)

				# Otherwise, copy original to renamed
				elif path != path_new:
					shutil.copy (os.path.join (work, path), os.path.join (work, path_new))

					deletes.append (path)

			# Apply filtering command if any
			if modifier.filter is not None and (modifier.filter == '' or self.run (work, path, modifier.filter) is None):
				logger.debug ('File \'{0}\' filtered out.'.format (path))

				type = Action.NOP

			# Append action to list and return
			actions.append (Action (path_new, type))

			return (actions, deletes)

		# No modifier matched, return unmodified input
		return ([Action (path, type)], [])

	def run (self, work, path, command):
		result = Process (command.replace ('{}', path)) \
			.set_directory (work) \
			.set_shell (True) \
			.execute ()

		if not result:
			return None

		return result.out
