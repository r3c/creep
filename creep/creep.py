#!/usr/bin/env python

import argparse
import logging
import os
import src
import sys

def main ():
	# Parse command line options
	parser = argparse.ArgumentParser (description = 'Perform incremental deployment from Git/plain workspace to FTP/SSH/local folder.')
	parser.add_argument ('name', nargs = '*', help = 'Deploy to specified named location (* = everywhere)')
	parser.add_argument ('-a', '--append-file', action = 'append', default = [], help = 'Manually append file or directory to locations', metavar = 'PATH')
	parser.add_argument ('--extra-append', action = 'append', default = [], help = argparse.SUPPRESS)
	parser.add_argument ('-e', '--environment', action = 'store', default = '.creep.env', help = 'Use specified environment file', metavar = 'PATH')
	parser.add_argument ('-f', '--rev-from', action = 'store', help = 'Initial version used to compute diff', metavar = 'REV')
	parser.add_argument ('-d', '--definition', action = 'store', default = '.creep.def', help = 'Use specified definition file', metavar = 'PATH')
	parser.add_argument ('-q', '--quiet', dest = 'level', action = 'store_const', const = logging.CRITICAL + 1, default = logging.INFO, help = 'Disable logging')
	parser.add_argument ('-r', '--remove-file', action = 'append', default = [], help = 'Manually remove file or directory from locations', metavar = 'PATH')
	parser.add_argument ('--extra-remove', action = 'append', default = [], help = argparse.SUPPRESS)
	parser.add_argument ('-t', '--rev-to', action = 'store', help = 'Target version used to compute diff', metavar = 'REV')
	parser.add_argument ('-v', '--verbose', dest = 'level', action = 'store_const', const = logging.DEBUG, default = logging.INFO, help = 'Increase verbosity')
	parser.add_argument ('-y', '--yes', action = 'store_true', help = 'Always answer yes to prompts')

	args = parser.parse_args ()

	# Initialize logger
	logger = src.Logger.build ()
	logger.setLevel (args.level)

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
	elif len (args.name) == 1 and args.name[0] == '*':
		args.name = environment.locations.keys ()

	code = 0

	for name in args.name:
		append_files = args.append_file + args.extra_append
		remove_files = args.remove_file + args.extra_append

		if not src.Deploy.execute (logger, definition, environment, name, append_files, remove_files, args.rev_from, args.rev_to, args.yes):
			code = 2

	return code

if __name__ == '__main__':
	sys.exit (main ())
