#!/usr/bin/env python

import argparse
import logging
import os
import shutil
import src
import sys
import tempfile

def deploy (logger, environments, modifiers, name, files, rev_from, rev_to):
	# Retrieve remove location by name
	location = environments.get_location (name)

	if location is None:
		logger.error ('There is no location "{0}" in your environments file.'.format (name))

		return False

	# Build target from location connection string
	target = src.target.build (logger, location.connection, location.options)

	if target is None:
		logger.error ('Unsupported scheme in connection string "{1}" for location "{0}".'.format (name, location.connection))

		return False

	# Read revisions file
	if not location.local:
		data = target.read (logger, location.state)
	elif os.path.exists (location.state):
		data = open (location.state, 'rb').read ()
	else:
		data = ''

	if data is None:
		logger.error ('Can\'t read contents from revisions file "{1}" for location "{0}".'.format (name, location.state))

		return False

	try:
		revisions = src.Revisions (data)
	except Error as e:
		logger.error ('Can\'t parse revisions from file "{1}" for location "{0}": {2}.'.format (name, location.state, e))

		return False

	# Build source repository reader from current directory
	source = src.source.build (environments.source, environments.options, os.getcwd ())

	if source is None:
		logger.error ('Unknown source type in folder "{1}" for location "{0}", try specifying "source" option in environments file.'.format (name, os.getcwd ()))

		return False

	# Retrieve source and target revisions
	if rev_from is None:
		rev_from = revisions.get (name)

		if rev_from is None and not prompt (logger, 'No current revision found for location "{0}", maybe you\'re deploying for the first time. Initiate full deploy? [Y/N]'.format (name)):
			return True

	if rev_to is None:
		rev_to = source.current ()

		if rev_to is None:
			logger.error ('Can\'t find source version for location "{0}", please ensure your environments file is correctly defined.'.format (name))

			return False

	revisions.set (name, rev_to)

	# Prepare actions
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
			action.prepare (work)

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

		# Update current revision (remote mode)
		if rev_from != rev_to and not location.local:
			with open (os.path.join (work, location.state), 'wb') as file:
				file.write (revisions.serialize ())

			actions.append (src.Action (location.state, src.Action.ADD))

		# Display processed actions using console target
		if len (actions) < 1:
			logger.info ('No deployment required for location "{0}".'.format (name))

			return True

		from src.targets.console import ConsoleTarget

		console = ConsoleTarget ()
		console.send (logger, work, actions)

		if not prompt (logger, 'Execute synchronization? [Y/N]'):
			return True

		# Execute processed actions starting with "DEL" ones
		actions.sort (key = lambda action: (action.type != src.Action.DEL and 1 or 0, action.path))

		if not target.send (logger, work, actions):
			return False

		# Update current revision (local mode)
		if location.local:
			with open (location.state, 'wb') as file:
				file.write (revisions.serialize ())

		logger.info ('Deployment to location "{0}" done.'.format (name))

		return True

	finally:
		shutil.rmtree (work)

def main ():
	global yes

	# Parse command line options
	parser = argparse.ArgumentParser (description = 'Perform full or incremental deployment, from Git/plain workspace to FTP/SSH/local folder.')
	parser.add_argument ('names', nargs = '*', help = 'Specify target location name')
	parser.add_argument ('-a', '--extra-add', action = 'append', default = [], help = 'Extra local file/dir to add', metavar = 'PATH')
	parser.add_argument ('-d', '--extra-del', action = 'append', default = [], help = 'Extra local file/dir to delete', metavar = 'PATH')
	parser.add_argument ('-e', '--envs', action = 'store', default = '.creep.envs', help = 'Use specified environments file', metavar = 'PATH')
	parser.add_argument ('-f', '--rev-from', action = 'store', help = 'Initial version used to compute diff', metavar = 'REV')
	parser.add_argument ('-m', '--mods', action = 'store', default = '.creep.mods', help = 'Use specified modifiers file', metavar = 'PATH')
	parser.add_argument ('-q', '--quiet', dest = 'level', action = 'store_const', const = logging.CRITICAL + 1, default = logging.INFO, help = 'Disable logging')
	parser.add_argument ('-t', '--rev-to', action = 'store', help = 'Target version used to compute diff', metavar = 'REV')
	parser.add_argument ('-v', '--verbose', dest = 'level', action = 'store_const', const = logging.DEBUG, default = logging.INFO, help = 'Increase verbosity')
	parser.add_argument ('-y', '--yes', action = 'store_true', help = 'Always answer yes to prompts')

	args = parser.parse_args ()

	# Initialize logger
	logger = src.Logger.build ()
	logger.setLevel (args.level)

	# Build extra files list
	files = []

	for path in args.extra_add:
		if os.path.isdir (path):
			for (dirpath, dirnames, filenames) in os.walk (path):
				files.extend ((src.Action (os.path.join (dirpath, filename), src.Action.ADD) for filename in filenames))
		elif os.path.isfile (path):
			files.append (src.Action (path, src.Action.ADD))
		else:
			logger.error ('Can\'t add missing file "{0}".'.format (path))

	for path in args.extra_del:
		if os.path.isdir (path):
			for (dirpath, dirnames, filenames) in os.walk (path):
				files.extend ((src.Action (os.path.join (dirpath, filename), src.Action.DEL) for filename in filenames))
		else:
			files.append (src.Action (path, src.Action.DEL))

	# Perform deployment
	environments = src.Environments (logger, args.envs)
	modifiers = src.Modifiers (args.mods, args.envs)
	yes = args.yes

	if len (args.names) < 1:
		args.names.append ('default')

	code = 0

	for name in args.names:
		if not deploy (logger, environments, modifiers, name, files, args.rev_from, args.rev_to):
			code = 1

	return code

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

if __name__ == '__main__':
	sys.exit (main ())
