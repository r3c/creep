#!/usr/bin/env python

import argparse
import creep
import logging
import os
import shutil
import sys
import tempfile

def deploy (logger, environment, modifiers, name, files, rev_from, rev_to):
	# Build target from environment connection string
	target = creep.target.build (environment.connection, environment.options)

	if target is None:
		logger.error ('Unsupported scheme in connection string "{1}" for environment "{0}"'.format (name, environment.connection))

		return False

	# Read revisions file
	if not environment.local:
		data = target.read (logger, environment.state)
	elif os.path.exists (environment.state):
		data = open (environment.state, 'rb').read ()
	else:
		data = None

	revisions = creep.Revisions (data)

	# Build source repository reader from current directory
	source = creep.source.build (environment.delta, os.getcwd ())

	if source is None:
		logger.error ('Can\'t recognize workspace type in folder "{1}" for environment "{0}"'.format (name, os.getcwd ()))

		return False

	# Retrieve source and target revisions
	if rev_from is None:
		rev_from = revisions.get (name)

		if rev_from is None and not prompt (logger, 'Could not read current revision, maybe you\'re deploying for the first time. Initiate full deploy? [Y/N]'):
			return True

	if rev_to is None:
		rev_to = source.current ()

		if rev_to is None:
			logger.error ('Can\'t find source version, please ensure your environment file is correctly defined')

			return False

	revisions.set (name, rev_to)

	# Prepare actions
	data = rev_from <> rev_to and revisions.serialize () or None
	work = tempfile.mkdtemp ()

	try:
		commands = []

		# Append commands from revision diff
		diff = source.diff (logger, work, rev_from, rev_to)

		if diff is None:
			return False

		commands.extend (diff)

		# Append commands from manually specified files
		for action in files:
			if action.type == creep.Action.ADD:
				path = os.path.join (work, action.path)

				if not os.path.isdir (os.path.dirname (path)):
					os.makedirs (os.path.dirname (path))

				shutil.copy (action.path, path)

		commands.extend (files)

		# Apply pre-processing modifiers on actions
		actions = []
		deletes = []
		used = set ()

		for command in commands:
			(actions_append, deletes_append) = modifiers.apply (logger, work, command.path, command.type, used)

			actions.extend (actions_append)
			deletes.extend (deletes_append)

		for delete in deletes:
			os.remove (os.path.join (work, delete))

		# Update current revision (remove mode)
		if data is not None and not environment.local:
			with open (os.path.join (work, environment.state), 'wb') as file:
				file.write (data)

			actions.append (creep.Action (environment.state, creep.Action.ADD))

		# Display processed actions using console target
		if len (actions) < 1:
			logger.info ('No synchronization action required')

			return True

		from creep.targets.console import ConsoleTarget

		console = ConsoleTarget ()
		console.send (logger, work, actions)

		if not prompt (logger, 'Execute synchronization? [Y/N]'):
			return True

		# Execute processed actions starting with "DEL" ones
		actions.sort (key = lambda action: (action.type != creep.Action.DEL and 1 or 0, action.path))

		if not target.send (logger, work, actions):
			return False

		# Update current revision (local mode)
		if data is not None and environment.local:
			with open (environment.state, 'wb') as file:
				file.write (data)

		logger.info ('Deployment successfully completed')

		return True

	finally:
		shutil.rmtree (work)

def prompt (logger, question):
	global yes

	if yes:
		return True

	logger.info (question)

	while True:
		answer = raw_input ()

		if answer == 'N' or answer == 'n':
			return False
		elif answer == 'Y' or answer == 'y':
			return True

		logger.warning ('Invalid answer')

# Parse command line options
parser = argparse.ArgumentParser (description = 'Perform full or incremental deployment, from Git/plain workspace to FTP/SSH/local folder.')
parser.add_argument ('names', nargs = '*', help = 'Specify target environment name')
parser.add_argument ('-a', '--extra-add', action = 'append', default = [], help = 'Extra local file/dir to add', metavar = 'PATH')
parser.add_argument ('-d', '--extra-del', action = 'append', default = [], help = 'Extra local file/dir to delete', metavar = 'PATH')
parser.add_argument ('-e', '--envs', action = 'store', default = '.creep.envs', help = 'Environments file path', metavar = 'PATH')
parser.add_argument ('-f', '--rev-from', action = 'store', help = 'Initial version used to compute diff', metavar = 'REV')
parser.add_argument ('-m', '--mods', action = 'store', default = '.creep.mods', help = 'Modifiers file path', metavar = 'PATH')
parser.add_argument ('-t', '--rev-to', action = 'store', help = 'Target version used to compute diff', metavar = 'REV')
parser.add_argument ('-v', '--verbose', action = 'store_true', help = 'Increase verbosity')
parser.add_argument ('-y', '--yes', action = 'store_true', help = 'Always answer yes to prompts')

args = parser.parse_args ()

# Initialize logger
logger = creep.Logger.build ()
logger.setLevel (args.verbose and logging.DEBUG or logging.INFO)

# Build extra files list
files = []

for path in args.extra_add:
	if os.path.isdir (path):
		for (dirpath, dirnames, filenames) in os.walk (path):
			files.extend ((creep.Action (os.path.join (dirpath, filename), creep.Action.ADD) for filename in filenames))
	elif os.path.isfile (path):
		files.append (creep.Action (path, creep.Action.ADD))
	else:
		logger.error ('Can\'t add missing file \'{0}\''.format (path))

for path in args.extra_del:
	if os.path.isdir (path):
		for (dirpath, dirnames, filenames) in os.walk (path):
			files.extend ((creep.Action (os.path.join (dirpath, filename), creep.Action.DEL) for filename in filenames))
	else:
		files.append (creep.Action (path, creep.Action.DEL))

# Perform deployment
environments = creep.Environments (args.envs)
modifiers = creep.Modifiers (args.mods)
yes = args.yes

if len (args.names) < 1:
	args.names.append ('default')

code = 0

for name in args.names:
	# Retrieve environment configuration
	environment = environments.get (name)

	if environment is None:
		logger.error ('There is no environment \'{0}\' in your environments file'.format (name))

		code = 1
	elif not deploy (logger, environment, modifiers, name, files, args.rev_from, args.rev_to):
		logger.error ('Deployment to environment \'{0}\' failed'.format (name))

		code = 1

sys.exit (code)
