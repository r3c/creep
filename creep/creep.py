#!/usr/bin/env python

import argparse
import logging
import os
import src
import sys

def main ():
	# Parse command line options
	parser = argparse.ArgumentParser (description = 'Perform incremental deployment from Git/plain workspace to FTP/SSH/local folder.')
	parser.add_argument ('name', nargs = '*', help = 'Deploy to specified named location')
	parser.add_argument ('-a', '--extra-append', action = 'append', default = [], help = 'Manually append file or directory to locations', metavar = 'PATH')
	parser.add_argument ('-e', '--environment', action = 'store', default = '.creep.env', help = 'Use specified environment file', metavar = 'PATH')
	parser.add_argument ('-f', '--rev-from', action = 'store', help = 'Initial version used to compute diff', metavar = 'REV')
	parser.add_argument ('-d', '--definition', action = 'store', default = '.creep.def', help = 'Use specified definition file', metavar = 'PATH')
	parser.add_argument ('-q', '--quiet', dest = 'level', action = 'store_const', const = logging.CRITICAL + 1, default = logging.INFO, help = 'Disable logging')
	parser.add_argument ('-r', '--extra-remove', action = 'append', default = [], help = 'Manually remove file or directory from locations', metavar = 'PATH')
	parser.add_argument ('-t', '--rev-to', action = 'store', help = 'Target version used to compute diff', metavar = 'REV')
	parser.add_argument ('-v', '--verbose', dest = 'level', action = 'store_const', const = logging.DEBUG, default = logging.INFO, help = 'Increase verbosity')
	parser.add_argument ('-y', '--yes', action = 'store_true', help = 'Always answer yes to prompts')

	args = parser.parse_args ()

	# Initialize logger
	logger = src.Logger.build ()
	logger.setLevel (args.level)

	# Build extra files list
	files = []

	for path in args.extra_append:
		if os.path.isdir (path):
			for (dirpath, dirnames, filenames) in os.walk (path):
				files.extend ((src.Action (os.path.join (dirpath, filename), src.Action.ADD) for filename in filenames))
		elif os.path.isfile (path):
			files.append (src.Action (path, src.Action.ADD))
		else:
			logger.error ('Can\'t append missing file "{0}".'.format (path))

	for path in args.extra_remove:
		if os.path.isdir (path):
			for (dirpath, dirnames, filenames) in os.walk (path):
				files.extend ((src.Action (os.path.join (dirpath, filename), src.Action.DEL) for filename in filenames))
		else:
			files.append (src.Action (path, src.Action.DEL))

	# Load environment file or fail
	if os.path.isfile (args.environment):
		with open (args.environment, 'rb') as file:
			environment = src.Environment (file)
	else:
		logger.error ('No environment file "{0}" found.'.format (args.environment))

		return 1

	# Load definition file or use default
	if os.path.isfile (args.definition):
		with open (args.definition, 'rb') as file:
			definition = src.Definition (file, [args.environment, args.definition])
	else:
		definition = src.Definition (None, [args.environment, args.definition])

	# Perform deployment
	if len (args.name) < 1:
		args.name.append ('default')

	code = 0

	for name in args.name:
		if not src.Deploy.execute (logger, definition, environment, name, files, args.rev_from, args.rev_to, args.yes):
			code = 2

	return code

if __name__ == '__main__':
	sys.exit (main ())
