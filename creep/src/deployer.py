#!/usr/bin/env python

from . import factory, path
from .action import Action
from .definition import Definition
from .environment import Environment
from .revision import Revision

import codecs
import os
import shutil
import tempfile

class Deployer:
	def __init__ (self, logger, definition, environment, yes):
		self.definition = definition
		self.environment = environment
		self.logger = logger
		self.yes = yes

	def deploy (self, base_path, names, append_files, remove_files, rev_from, rev_to):
		# Ensure base directory is valid
		if not os.path.isdir (base_path):
			self.logger.error ('Base directory "{0}" doesn\'t exist.'.format (base_path))

			return False

		# Load environment configuration from command line argument or file
		ignores = []

		if self.environment[0:1] == '{':
			environment_json = self.environment
		else:
			environment_name = self.environment[0:1] == '@' and self.environment[1:] or self.environment
			environment_path = os.path.join (base_path, environment_name)

			if os.path.isfile (environment_path):
				reader = codecs.getreader ('utf-8')

				with open (environment_path, 'rb') as file:
					environment_json = reader (file).read ()
			else:
				self.logger.warning ('Environment file "{0}" doesn\'t exist.'.format (environment_path))

				return False

			ignores.append (environment_name)

		environment = Environment (environment_json)

		# Read definition configuration from command line argument or file
		if self.definition[0:1] == '{':
			definition_json = self.definition
		else:
			definition_name = self.definition[0:1] == '@' and self.definition[1:] or self.definition
			definition_path = os.path.join (base_path, definition_name)

			if os.path.isfile (definition_path):
				reader = codecs.getreader ('utf-8')

				with open (definition_path, 'rb') as file:
					definition_json = reader (file).read ()
			else:
				definition_json = '{}'

			ignores.append (definition_name)

		definition = Definition (definition_json, ignores)

		# Expand location names
		if len (names) < 1:
			names.append ('default')
		elif len (names) == 1 and names[0] == '*':
			names = environment.locations.keys ()

		# Deploy to target locations
		ok = True

		for name in names:
			location = environment.get_location (name)

			if location is None:
				self.logger.error ('There is no location "{0}" in your environment file.'.format (name))

				continue

			if location.connection is not None:
				self.logger.info ('Deploying to location "{0}"...'.format (name))

				if not self.sync (base_path, definition, location, name, append_files, remove_files, rev_from, rev_to):
					ok = False

					continue

			for cascade_path, cascade_names in location.cascades.items ():
				full_path = os.path.join (base_path, cascade_path)

				self.logger.info ('Cascading to path "{0}"...'.format (full_path))
				self.logger.enter ()

				ok = self.deploy (full_path, cascade_names, [], [], None, None) and ok

				self.logger.leave ()

		return ok

	def prompt (self, question):
		self.logger.info (question)

		while True:
			answer = input ()

			if answer == 'N' or answer == 'n':
				return False
			elif answer == 'Y' or answer == 'y':
				return True

			self.logger.warning ('Invalid answer')

	def sync (self, base_path, definition, location, name, append_files, remove_files, rev_from, rev_to):
		# Build source repository reader from current directory
		source = factory.create_source (definition.source, definition.options, base_path)

		if source is None:
			self.logger.error ('Unknown source type in folder "{0}", try specifying "source" option in definition file.'.format (base_path))

			return False

		# Build target from location connection string
		target = factory.create_target (self.logger, location.connection, location.options, base_path)

		if target is None:
			self.logger.error ('Unsupported scheme in connection string "{0}".'.format (location.connection))

			return False

		# Read revision file
		if not location.local:
			data = target.read (self.logger, location.state)
		elif os.path.exists (os.path.join (base_path, location.state)):
			data = open (os.path.join (base_path, location.state), 'rb').read ()
		else:
			data = ''

		if data is None:
			self.logger.error ('Can\'t read revision file "{0}", check connection string and ensure parent directory exists.'.format (location.state))

			return False

		try:
			revision = Revision (data)
		except Exception as e:
			self.logger.error ('Can\'t parse revision from file "{0}": {1}.'.format (location.state, e))

			return False

		# Retrieve source and target revision
		if rev_from is None:
			rev_from = revision.get (name)

			if rev_from is None and not self.yes and not self.prompt ('No current revision found, maybe you\'re deploying for the first time. Initiate full deploy? [Y/N]'):
				return True

		if rev_to is None:
			rev_to = source.current (base_path)

			if rev_to is None:
				self.logger.error ('Can\'t find source version, please ensure your environment file is correctly defined.')

				return False

		revision.set (name, rev_to)

		# Prepare actions
		work_path = tempfile.mkdtemp ()

		try:
			# Append actions from revision diff
			source_actions = source.diff (self.logger, base_path, work_path, rev_from, rev_to)

			if source_actions is None:
				return False

			# Append actions for manually specified files
			manual_actions = []

			for append in location.append_files + append_files:
				full_path = os.path.join (base_path, append)

				if os.path.isdir (full_path):
					for (dirpath, dirnames, filenames) in os.walk (full_path):
						parent_path = os.path.relpath (dirpath, base_path)

						manual_actions.extend ((Action (os.path.join (parent_path, filename), Action.ADD) for filename in filenames))
				elif os.path.isfile (full_path):
					manual_actions.append (Action (append, Action.ADD))
				else:
					self.logger.warning ('Can\'t append missing file "{0}".'.format (append))

			for action in manual_actions:
				if not path.duplicate (os.path.join (base_path, action.path), work_path, action.path):
					self.logger.warning ('Can\'t copy file "{0}".'.format (action.path))

			for remove in location.remove_files + remove_files:
				full_path = os.path.join (base_path, remove)

				if os.path.isdir (full_path):
					for (dirpath, dirnames, filenames) in os.walk (full_path):
						parent_path = os.path.relpath (dirpath, base_path)

						manual_actions.extend ((Action (os.path.join (parent_path, filename), Action.DEL) for filename in filenames))
				else:
					manual_actions.append (Action (remove, Action.DEL))

			# Apply pre-processing modifiers on actions
			actions = []
			cancels = []
			used = set ()

			for command in source_actions + manual_actions:
				(actions_append, cancels_append) = definition.apply (self.logger, work_path, command.path, command.type, used)

				actions.extend (actions_append)
				cancels.extend (cancels_append)

			for cancel in cancels:
				path.remove (work_path, cancel)

			# Update current revision (remote mode)
			if rev_from != rev_to and not location.local:
				with open (os.path.join (work_path, location.state), 'wb') as file:
					file.write (revision.serialize ().encode ('utf-8'))

				actions.append (Action (location.state, Action.ADD))

			# Display processed actions using console target
			if len (actions) < 1:
				self.logger.info ('No deployment required.')

				return True

			from .targets.console import ConsoleTarget

			console = ConsoleTarget ()
			console.send (self.logger, work_path, actions)

			if not self.yes and not self.prompt ('Deploy? [Y/N]'):
				return True

			# Execute processed actions after ordering them by precedence
			actions.sort (key = lambda action: (action.order (), action.path))

			if not target.send (self.logger, work_path, actions):
				return False

			# Update current revision (local mode)
			if location.local:
				with open (os.path.join (base_path, location.state), 'wb') as file:
					file.write (revision.serialize ().encode ('utf-8'))

		finally:
			shutil.rmtree (work_path)

		self.logger.info ('Deployment done.')

		return True

# Hack for Python 2 + 3 compatibility
try:
	input = raw_input
except NameError:
	pass
