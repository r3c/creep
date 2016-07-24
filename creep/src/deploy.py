#!/usr/bin/env python

from action import Action
from revision import Revision
from source import Source
from target import Target

import os
import shutil
import tempfile

class Deploy:
	@staticmethod
	def execute (logger, definition, environment, name, append_files, remove_files, rev_from, rev_to, yes):
		# Retrieve remote location by name
		location = environment.get_location (name)

		if location is None:
			logger.error ('There is no location "{0}" in your environment file.'.format (name))

			return False

		# Build target from location connection string
		target = Target.build (logger, location.connection, location.options)

		if target is None:
			logger.error ('Unsupported scheme in connection string "{1}" for location "{0}".'.format (name, location.connection))

			return False

		# Read revision file
		if not location.local:
			data = target.read (logger, location.state)
		elif os.path.exists (location.state):
			data = open (location.state, 'rb').read ()
		else:
			data = ''

		if data is None:
			logger.error ('Can\'t read contents of revision file "{1}" from location "{0}".'.format (name, location.state))

			return False

		try:
			revision = Revision (data)
		except Error as e:
			logger.error ('Can\'t parse revision from file "{1}" from location "{0}": {2}.'.format (name, location.state, e))

			return False

		# Build source repository reader from current directory
		source = Source.build (definition.source, definition.options, os.getcwd ())

		if source is None:
			logger.error ('Unknown source type in folder "{0}", try specifying "source" option in environment file.'.format (os.getcwd ()))

			return False

		# Retrieve source and target revision
		if rev_from is None:
			rev_from = revision.get (name)

			if rev_from is None and not yes and not Deploy.prompt (logger, 'No current revision found for location "{0}", maybe you\'re deploying for the first time. Initiate full deploy? [Y/N]'.format (name)):
				return True

		if rev_to is None:
			rev_to = source.current ()

			if rev_to is None:
				logger.error ('Can\'t find source version for location "{0}", please ensure your environment file is correctly defined.'.format (name))

				return False

		revision.set (name, rev_to)

		# Prepare actions
		work = tempfile.mkdtemp ()

		try:
			commands = []

			# Append actions from revision diff
			source_actions = source.diff (logger, work, rev_from, rev_to)

			if source_actions is None:
				return False

			commands.extend (source_actions)

			# Append actions for manually specified files
			extra_actions = []

			for path in location.append_files + append_files:
				if os.path.isdir (path):
					for (dirpath, dirnames, filenames) in os.walk (path):
						extra_actions.extend ((src.Action (os.path.join (dirpath, filename), src.Action.ADD) for filename in filenames))
				elif os.path.isfile (path):
					extra_actions.append (src.Action (path, src.Action.ADD))
				else:
					logger.warning ('Can\'t append missing file "{0}".'.format (path))

			for action in extra_actions:
				action.prepare (work)

			for path in location.remove_files + remove_files:
				if os.path.isdir (path):
					for (dirpath, dirnames, filenames) in os.walk (path):
						extra_actions.extend ((src.Action (os.path.join (dirpath, filename), src.Action.DEL) for filename in filenames))
				else:
					extra_actions.append (src.Action (path, src.Action.DEL))

			commands.extend (extra_actions)

			# Apply pre-processing modifiers on actions
			actions = []
			deletes = []
			used = set ()

			for command in commands:
				(actions_append, deletes_append) = definition.apply (logger, work, command.path, command.type, used)

				actions.extend (actions_append)
				deletes.extend (deletes_append)

			for delete in deletes:
				os.remove (os.path.join (work, delete))

			# Update current revision (remote mode)
			if rev_from != rev_to and not location.local:
				with open (os.path.join (work, location.state), 'wb') as file:
					file.write (revision.serialize ())

				actions.append (Action (location.state, Action.ADD))

			# Display processed actions using console target
			if len (actions) < 1:
				logger.info ('No deployment required for location "{0}".'.format (name))

				return True

			from targets.console import ConsoleTarget

			console = ConsoleTarget ()
			console.send (logger, work, actions)

			if not yes and not Deploy.prompt (logger, 'Execute synchronization? [Y/N]'):
				return True

			# Execute processed actions starting with "DEL" ones
			actions.sort (key = lambda action: (action.type != Action.DEL and 1 or 0, action.path))

			if not target.send (logger, work, actions):
				return False

			# Update current revision (local mode)
			if location.local:
				with open (location.state, 'wb') as file:
					file.write (revision.serialize ())

			logger.info ('Deployment to location "{0}" done.'.format (name))

			return True

		finally:
			shutil.rmtree (work)

	@staticmethod
	def prompt (logger, question):
		logger.info (question)

		while True:
			answer = raw_input ()

			if answer == 'N' or answer == 'n':
				return False
			elif answer == 'Y' or answer == 'y':
				return True

			logger.warning ('Invalid answer')
