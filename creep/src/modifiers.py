#!/usr/bin/env python

import json
import os
import re

from action import Action
from process import Process

class ModifierRule:
	def __init__ (self, regex, filter, rename, modify, link):
		self.filter = filter
		self.link = link
		self.modify = modify
		self.regex = regex
		self.rename = rename

class Modifiers:
	def __init__ (self, path, environments):
		# Read rules from configuration file if available...
		if os.path.isfile (path):
			rules = []

			with open (path, 'rb') as stream:
				for rule in json.load (stream):
					modify = rule.get ('modify', rule.get ('adapt', None))
					filter = rule.get ('filter', None)
					link = rule.get ('link', None)
					rename = rule.get ('rename', rule.get ('name', None))

					rules.append (ModifierRule (re.compile (rule['pattern']), filter, rename, modify, link))

		# ...or provide default set of rules otherwise
		else:
			rules = [ModifierRule (re.compile (re.escape (environments)), 'false', None, None, None)]

		self.rules = rules

	def apply (self, logger, work, path, type, used):
		# Ensure we don't process a file already scanned
		path = os.path.normpath (path)

		if path in used:
			return ([], [])

		used.add (path)

		# Find rule matching current file name if any
		name = os.path.basename (path)

		for rule in self.rules:
			match = rule.regex.search (name)

			if match is None:
				continue

			logger.debug ('File \'{0}\' matches \'{1}\'.'.format (path, rule.regex.pattern))

			actions = []
			deletes = []

			# Apply renaming pattern if any
			if rule.rename is not None:
				name = os.path.basename (re.sub ('\\\\([0-9]+)', lambda m: match.group (int (m.group (1))), rule.rename))

				logger.debug ('File \'{0}\' renamed to \'{1}\'.'.format (path, name))

			path_new = os.path.normpath (os.path.join (os.path.dirname (path), name))

			if type == Action.ADD:
				# Apply link command if any
				if rule.link is not None:
					out = self.run (work, path, rule.link)

					if out is not None:
						for link in out.splitlines ():
							logger.debug ('File \'{0}\' is linked to file \'{1}\'.'.format (path, link))

							(actions_append, deletes_append) = self.apply (logger, work, link, type, used)

							actions.extend (actions_append)
							deletes.extend (deletes_append)
					else:
						logger.debug ('Command \'link\' on file \'{0}\' returned non-zero code.'.format (path))

				# Build output file using processing command if any
				if rule.modify is not None:
					out = self.run (work, path, rule.modify)

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
			if rule.filter is not None and self.run (work, path, rule.filter) is None:
				logger.debug ('File \'{0}\' filtered out.'.format (path))

				type = Action.NOP

			# Append action to list and return
			actions.append (Action (path_new, type))

			return (actions, deletes)

		# No rule matched, return unmodified input
		return ([Action (path, type)], [])

	def run (self, work, path, command):
		return (
			Process (command.replace ('{}', path))
				.set_directory (work)
				.set_shell (True)
				.execute ()
		)
