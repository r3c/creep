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
		logger.error ('Unsupported environment connection string "{0}"'.format (environment.connection))

		return False

	# Read revisions file
	if not environment.local:
		data = target.read (logger, environment.revisions)
	elif os.path.exists (environment.revisions):
		data = open (environment.revisions, 'rb').read ()
	else:
		data = None

	revisions = creep.Revisions (data)

	# Build source repository reader from current directory
	source = creep.source.build (os.getcwd ())

	if source is None:
		logger.error ('Can\'t recognize supported workspace in directory "{0}"'.format (os.getcwd ()))

		return False

	# Retrieve source and target revisions
	if rev_from is None:
		rev_from = revisions.get (name)

		if rev_from is None and not prompt (logger, 'Could not read revision, initiate full deploy? [Y/N]'):
			return True

	if rev_to is None:
		rev_to = source.current ()

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
			if action.type == creep.Action.ADD:
				shutil.copyfile (action.path, os.path.join (work, action.path))

			commands.append (action)

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

		if len (actions) < 1:
			logger.info ('No action')

			return True

		# Display processed actions using console target
		from creep.targets.console import ConsoleTarget

		console = ConsoleTarget ()
		console.send (logger, work, actions)

		if not prompt (logger, 'Execute synchronization? [Y/N]'):
			return True

		# Execute processed actions using actual target
		data = revisions.serialize ()

		if not environment.local:
			with open (os.path.join (work, environment.revisions), 'wb') as file:
				file.write (data)

			actions.append (creep.Action (environment.revisions, creep.Action.ADD))

		if not target.send (logger, work, actions):
			return False

		if environment.local:
			with open (environment.revisions, 'wb') as file:
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
parser = argparse.ArgumentParser (description = 'Perform full or incremental deployment, from Git/SVN/plain workspace to FTP/SSH/local remote.')
parser.add_argument ('names', nargs = '*', help = 'Specify target environment name')
parser.add_argument ('-a', '--extra-add', action = 'append', default = [], help = 'Extra local file to add', metavar = 'PATH')
parser.add_argument ('-d', '--extra-del', action = 'append', default = [], help = 'Extra local file to delete', metavar = 'PATH')
parser.add_argument ('-e', '--envs', action = 'store', default = '.creep.envs', help = 'Environments file path', metavar = 'PATH')
parser.add_argument ('-f', '--rev-from', action = 'store', help = 'Initial version used to compute diff', metavar = 'REV')
parser.add_argument ('-m', '--mods', action = 'store', default = '.creep.mods', help = 'Modifiers file path', metavar = 'PATH')
parser.add_argument ('-t', '--rev-to', action = 'store', help = 'Target version used to compute diff', metavar = 'REV')
parser.add_argument ('-v', '--verbose', action = 'store_true', help = 'Increase verbosity')
parser.add_argument ('-y', '--yes', action = 'store_true', help = 'Always answer yes to prompts')

args = parser.parse_args ()

# Build extra files list
files = []

for path in args.extra_add:
	files.append (creep.Action (path, creep.Action.ADD))

for path in args.extra_del:
	files.append (creep.Action (path, creep.Action.DEL))

# Perform deployment
logger = creep.Logger.build ()
logger.setLevel (args.verbose and logging.DEBUG or logging.INFO)

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
		logger.error ('No environment \'{0}\''.format (name))

		code = 1
	elif not deploy (logger, environment, modifiers, name, files, args.rev_from, args.rev_to):
		logger.error ('Deployment to environment \'{0}\' failed'.format (name))

		code = 1

sys.exit (code)
